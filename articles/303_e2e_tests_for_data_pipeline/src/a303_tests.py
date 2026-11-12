"""303：処理に16個の不具合と2個の無害な書き換えを1つずつ入れ、5種類のテストがそれぞれ鳴るかを数える。
テスト：T1 関数ごとのテスト／T2 出力の形の点検／T3 入力と出力の合計の照合／
T4 手で作った小さな入力での通しテスト（期待する出力は DuckDB の SQL で別に計算）／T5 本番に似せた入力の一部での通しテスト（正しい版の出力を控えておく）
"""
import json
import duckdb, numpy as np, pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import pipeline as P
from common import DATA, RES, BLUE, ORANGE, GRAY, INK, save

SEED = 303
SRC = "架空のデータ（作成者が乱数で作成、seed 303）"
rng = np.random.default_rng(SEED)

# ---------- 架空のデータ（本番に似せたもの）
def make_orders(n):
    stores = [f"S{i:03d}" for i in range(1, 41)]
    t0 = pd.Timestamp("2025-01-01"); secs = rng.integers(0, 365 * 86400, n)
    df = pd.DataFrame({
        "order_id": np.arange(1, n + 1),
        "ordered_at_utc": (t0 + pd.to_timedelta(secs, unit="s")).strftime("%Y-%m-%d %H:%M:%S"),
        "store_code": rng.choice(stores, n),
        "customer_id": rng.integers(1, max(n // 3, 5), n),
        "amount": rng.integers(300, 30000, n).astype(float),
        "tax_included": (rng.random(n) < 0.7).astype(int),
        "status": rng.choice(["PAID", "PAID", "PAID", "PAID", "SHIPPED", "CANCELLED"], n),
    })
    df["updated_at"] = df.ordered_at_utc
    # 現実に起きる汚れ（割合は小さい）
    r = rng.random(n)
    df.loc[r < 0.01, "store_code"] = df.loc[r < 0.01, "store_code"].str.lower()
    df.loc[(r >= 0.01) & (r < 0.02), "store_code"] = " " + df.loc[(r >= 0.01) & (r < 0.02), "store_code"] + " "
    df.loc[(r >= 0.02) & (r < 0.025), "store_code"] = "S999"                       # マスタにない店
    df.loc[(r >= 0.03) & (r < 0.034), "amount"] = np.nan
    df.loc[(r >= 0.04) & (r < 0.043), "status"] = "Cancelled"
    dup = df.sample(frac=0.01, random_state=SEED).copy()                            # あとから更新された注文（金額や状態が変わる）
    dup["updated_at"] = (pd.to_datetime(dup.updated_at) + pd.Timedelta(days=2)).dt.strftime("%Y-%m-%d %H:%M:%S")
    dup["amount"] = (dup.amount * rng.uniform(0.5, 1.5, len(dup))).round(0)
    return pd.concat([df, dup], ignore_index=True).sample(frac=1, random_state=SEED).reset_index(drop=True)

def make_master(dup=True):
    codes = [f"S{i:03d}" for i in range(1, 41)]
    m = pd.DataFrame({"store_code": codes, "region": rng.choice(["北", "東", "西", "南"], 40)})
    if dup:
        m = pd.concat([m, pd.DataFrame({"store_code": ["S007"], "region": [m.region[6]]})], ignore_index=True)   # 同じ店が2行（閉店前と移転後など）
    return m

orders = make_orders(20000); master = make_master()
orders.to_csv(DATA / "orders.csv", index=False); master.to_csv(DATA / "store_master.csv", index=False)

# ---------- T4：手で作った小さな入力（仕様の1〜8を1つずつ突く24行）
H = [  # order_id, ordered_at_utc, store, customer, amount, tax_included, status, updated_at
 (1, "2025-01-10 03:00:00", "S001", 1, 1000, 1, "PAID", "2025-01-10 03:00:00"),
 (2, "2025-01-10 04:00:00", "s001", 1, 2000, 1, "PAID", "2025-01-10 04:00:00"),            # 小文字の店コード・同じ顧客
 (3, "2025-01-11 04:00:00", " S001 ", 2, 505, 0, "PAID", "2025-01-11 04:00:00"),           # 空白つき・税抜き（555.5）
 (4, "2025-01-12 04:00:00", "S001", 3, 505, 0, "PAID", "2025-01-12 04:00:00"),             # 税抜き（合わせて1111）
 (5, "2025-01-31 15:30:00", "S001", 4, 3000, 1, "PAID", "2025-01-31 15:30:00"),            # 日本時間では2月1日 0:30
 (6, "2025-01-31 14:30:00", "S001", 5, 4000, 1, "PAID", "2025-01-31 14:30:00"),            # 日本時間では1月31日 23:30
 (7, "2025-01-15 00:00:00", "S002", 6, 5000, 1, "CANCELLED", "2025-01-15 00:00:00"),
 (8, "2025-01-15 00:00:00", "S002", 7, 6000, 1, "Cancelled", "2025-01-15 00:00:00"),        # 大文字小文字ちがい
 (9, "2025-01-16 00:00:00", "S002", 8, 7000, 1, "PAID", "2025-01-16 00:00:00"),
 (9, "2025-01-16 00:00:00", "S002", 8, 7500, 1, "PAID", "2025-01-18 00:00:00"),            # 同じ注文の更新（新しいほうを使う）
 (10, "2025-01-17 00:00:00", "S002", 9, 800, 1, "PAID", "2025-01-17 00:00:00"),
 (10, "2025-01-17 00:00:00", "S002", 9, 800, 1, "CANCELLED", "2025-01-19 00:00:00"),       # あとから取消
 (11, "2025-01-20 00:00:00", "S002", 10, None, 1, "PAID", "2025-01-20 00:00:00"),          # 金額が空
 (12, "2025-01-21 00:00:00", "S999", 11, 900, 1, "PAID", "2025-01-21 00:00:00"),           # マスタにない店
 (13, "2025-01-22 00:00:00", "S003", 12, 1200, 1, "PAID", "2025-01-22 00:00:00"),          # マスタに2行ある店
 (14, "2025-02-03 00:00:00", "S003", 12, 1300, 1, "SHIPPED", "2025-02-03 00:00:00"),
 (15, "2025-02-04 00:00:00", "S001", 1, 333, 0, "PAID", "2025-02-04 00:00:00"),            # 税抜き 366.3
 (16, "2025-02-05 00:00:00", "S001", 2, 333, 0, "PAID", "2025-02-05 00:00:00"),            # 税抜き 366.3（合計 732.6→733、行ごとだと732）
 (17, "2025-02-06 00:00:00", "S002", 6, 2500, 1, "PAID", "2025-02-06 00:00:00"),
 (18, "2025-02-28 15:00:00", "S002", 7, 2600, 1, "PAID", "2025-02-28 15:00:00"),           # 日本時間では3月1日 0:00
 (19, "2025-03-01 02:00:00", "S002", 7, 2700, 1, "PAID", "2025-03-01 02:00:00"),
 (20, "2025-03-02 02:00:00", "s003", 13, 100, 1, "PAID", "2025-03-02 02:00:00"),
 (21, "2025-03-03 02:00:00", "S001", 14, 0, 1, "PAID", "2025-03-03 02:00:00"),             # 0円の注文（件数には入る）
 (22, "2025-03-04 02:00:00", "S001", 14, 150, 1, "PAID", "2025-03-04 02:00:00"),
]
hand = pd.DataFrame(H, columns=["order_id", "ordered_at_utc", "store_code", "customer_id", "amount", "tax_included", "status", "updated_at"])
hand_master = pd.DataFrame({"store_code": ["S001", "S002", "S003", "S003"], "region": ["東", "西", "南", "南"]})
hand.to_csv(DATA / "golden_input_orders.csv", index=False); hand_master.to_csv(DATA / "golden_input_master.csv", index=False)

# 期待する出力は、処理（pandas）とは別に、仕様から SQL で書いて計算する
SPEC_SQL = """
WITH o AS (SELECT *, upper(trim(store_code)) AS sc,
                  row_number() OVER (PARTITION BY order_id ORDER BY updated_at DESC) AS rn FROM orders),
     v AS (SELECT * FROM o WHERE rn = 1 AND upper(status) <> 'CANCELLED' AND amount IS NOT NULL),
     m AS (SELECT DISTINCT upper(trim(store_code)) AS sc, first(region) AS region FROM master GROUP BY 1)
SELECT strftime(CAST(ordered_at_utc AS TIMESTAMP) + INTERVAL 9 HOUR, '%Y-%m') AS month,
       coalesce(m.region, '不明') AS region,
       (sum(CASE WHEN tax_included = 1 THEN CAST(amount AS BIGINT) * 10 ELSE CAST(amount AS BIGINT) * 11 END) + 5) // 10 AS sales,
       count(*) AS orders, count(DISTINCT customer_id) AS customers
FROM v LEFT JOIN m ON v.sc = m.sc GROUP BY 1, 2 ORDER BY 1, 2
"""
def spec(o, m):
    con = duckdb.connect(); con.register("orders", o); con.register("master", m)
    return con.execute(SPEC_SQL).df()
golden_expected = spec(hand, hand_master)
golden_expected.to_csv(DATA / "golden_expected.csv", index=False)

def same(a, b):          # 行の順・列の順も含めて、ぴったり同じか
    try:
        pd.testing.assert_frame_equal(a.reset_index(drop=True), b.reset_index(drop=True), check_dtype=False)
        return True
    except AssertionError:
        return False
def same_loose(a, b):    # 列の順・行の順は問わず、中身が同じか
    if set(a.columns) != set(b.columns) or len(a) != len(b):
        return False
    c = sorted(a.columns)
    return same(a[c].sort_values(c).reset_index(drop=True), b[c].sort_values(c).reset_index(drop=True))

# 正しい版は、手で作った入力でも本番に似せた入力でも、SQL で書いた仕様と一致する（テストの土台の確認）
base_out, _ = P.run(hand, hand_master)
assert same(base_out, golden_expected), "正しい版が期待と合わない"
full_out, _ = P.run(orders, master)
assert same(full_out, spec(orders, master)), "正しい版が、2万行でも SQL の仕様と合わない"

# ---------- テスト（鳴れば True）
def t1_unit(bug):
    """関数ごとのテスト。各関数に、ふつうの入力を1〜2個（仕様の文をそのまま確かめる程度）"""
    f = []
    f.append(list(P.normalize_store(pd.Series([" s001 "]), bug)) != ["S001"])
    d = pd.DataFrame({"order_id": [1, 1], "updated_at": ["2025-01-01", "2025-01-02"], "v": ["old", "new"]})
    f.append(list(P.dedup_orders(d, bug).v) != ["new"])
    d = pd.DataFrame({"status": ["PAID", "CANCELLED"]}); f.append(len(P.drop_cancelled(d, bug)) != 1)
    d = pd.DataFrame({"amount": [100.0, None]}); o, n = P.clean_amount(d, bug); f.append(len(o) != 1 or n != 1)
    d = pd.DataFrame({"amount": [100.0, 100.0], "tax_included": [1, 0]}); f.append(list(P.to_tax_included(d, bug).amount_x10) != [1000, 1100])
    d = pd.DataFrame({"ordered_at_utc": ["2025-01-15 12:00:00"]}); f.append(list(P.order_month(d, bug).month) != ["2025-01"])
    d = pd.DataFrame({"store_code": ["S001"]}); m = pd.DataFrame({"store_code": ["S001"], "region": ["東"]}); f.append(list(P.join_region(d, m, bug).region) != ["東"])
    d = pd.DataFrame({"month": ["2025-01"] * 2, "region": ["東"] * 2, "amount_x10": [10, 20], "order_id": [1, 2], "customer_id": [1, 2]})
    a = P.aggregate(d, bug); f.append(not (int(a.sales.iloc[0]) == 3 and int(a.orders.iloc[0]) == 2 and int(a.customers.iloc[0]) == 2))
    return any(f)

def t2_shape(out):
    """出力の形の点検：列の名前、空の値、キーの重なり、行があるか、負の値"""
    need = {"month", "region", "sales", "orders", "customers"}
    if set(out.columns) != need or len(out) == 0: return True
    if out.isna().any().any() or out.duplicated(["month", "region"]).any(): return True
    if (out[["sales", "orders", "customers"]] < 0).any().any() or (out.customers > out.orders).any(): return True
    return not out.month.str.fullmatch(r"\d{4}-\d{2}").all()

def t3_reconcile(o, out):
    """入力と出力の合計の照合：使うはずの注文の件数と金額を、入力から別に数えて比べる"""
    con = duckdb.connect(); con.register("orders", o)
    n, s = con.execute("""WITH x AS (SELECT *, row_number() OVER (PARTITION BY order_id ORDER BY updated_at DESC) AS rn FROM orders)
        SELECT count(*), sum(CASE WHEN tax_included = 1 THEN CAST(amount AS BIGINT) * 10 ELSE CAST(amount AS BIGINT) * 11 END) / 10.0 FROM x
        WHERE rn = 1 AND upper(status) <> 'CANCELLED' AND amount IS NOT NULL""").fetchone()
    return int(out.orders.sum()) != n or abs(float(out.sales.sum()) - s) > len(out)     # 四捨五入の分（1行あたり0.5円まで）は許す

def evaluate(bug, o_big, m_big, sample, sample_expected):
    out_big, _ = P.run(o_big, m_big, bug)
    out_hand, _ = P.run(hand, hand_master, bug)
    out_samp, _ = P.run(sample, m_big, bug)
    return {"T1 関数ごと": t1_unit(bug), "T2 出力の形": t2_shape(out_big), "T3 合計の照合": t3_reconcile(o_big, out_big),
            "T4 通し（手で作った24行）": not same(out_hand, golden_expected), "T5 通し（本番に似せた500行）": not same(out_samp, sample_expected),
            "T4'（順は問わない）": not same_loose(out_hand, golden_expected)}

sample = orders.sample(500, random_state=SEED).reset_index(drop=True)
sample_expected, _ = P.run(sample, master)
rows = []
for b in P.BUGS + P.HARMLESS:
    rows.append({"bug": b, "kind": "無害" if b in P.HARMLESS else "不具合", **evaluate(b, orders, master, sample, sample_expected)})
M = pd.DataFrame(rows); M.to_csv(RES / "catch_matrix.csv", index=False)
T = [c for c in M.columns if c.startswith("T")]
bugs = M[M.kind == "不具合"]; harm = M[M.kind == "無害"]
summ = {t: {"caught": int(bugs[t].sum()), "of": int(len(bugs)), "false_alarm_on_harmless": int(harm[t].sum())} for t in T}
summ["T2+T3"] = {"caught": int((bugs["T2 出力の形"] | bugs["T3 合計の照合"]).sum()), "of": int(len(bugs))}
summ["T1+T2+T3"] = {"caught": int((bugs["T1 関数ごと"] | bugs["T2 出力の形"] | bugs["T3 合計の照合"]).sum()), "of": int(len(bugs))}
summ["T4_only"] = sorted(bugs[bugs["T4 通し（手で作った24行）"] & ~(bugs["T1 関数ごと"] | bugs["T2 出力の形"] | bugs["T3 合計の照合"])].bug)
summ["missed_by_T4"] = sorted(bugs[~bugs["T4 通し（手で作った24行）"]].bug)

# ---------- T5 は、入力の行数でどれだけ変わるか（行数ごとに30通りの抜き方）
size_rows = []
for n in (50, 200, 500, 2000, 10000):
    for rep in range(30):
        smp = orders.sample(n, random_state=1000 + rep).reset_index(drop=True)
        exp, _ = P.run(smp, master)
        c = sum(not same(P.run(smp, master, b)[0], exp) for b in P.BUGS)
        size_rows.append({"rows": n, "rep": rep, "caught": c})
S = pd.DataFrame(size_rows); S.to_csv(RES / "t5_by_sample_size.csv", index=False)
sz = S.groupby("rows").caught.agg(["mean", "min", "max"]).round(2)
summ["T5_by_rows"] = {int(k): {"mean": float(v["mean"]), "min": int(v["min"]), "max": int(v["max"])} for k, v in sz.iterrows()}
# 不具合ごとに、T5 が見つけた割合（行数別）
pb = []
for n in (50, 500, 10000):
    for b in P.BUGS:
        hit = 0
        for rep in range(30):
            smp = orders.sample(n, random_state=1000 + rep).reset_index(drop=True)
            hit += not same(P.run(smp, master, b)[0], P.run(smp, master)[0])
        pb.append({"rows": n, "bug": b, "caught_rate": hit / 30})
pd.DataFrame(pb).to_csv(RES / "t5_rate_by_bug.csv", index=False)
summ["n_orders"] = int(len(orders)); summ["golden_rows"] = int(len(hand))
json.dump(summ, open(RES / "a303_main.json", "w"), ensure_ascii=False, indent=1)
print(M.to_string()); print(json.dumps(summ, ensure_ascii=False, indent=1))

# ---------- 図1：不具合×テストの表
show = T[:5]
fig, ax = plt.subplots(figsize=(9, 6.6))
Z = M[show].astype(int).values
ax.imshow(Z, cmap=ListedColormap(["#f3f2ee", BLUE]), aspect="auto")
ax.set_xticks(range(len(show))); ax.set_xticklabels([s.replace("（", "\n（") for s in show], fontsize=9); ax.xaxis.tick_top()
ax.set_yticks(range(len(M))); ax.set_yticklabels(M.bug, fontsize=9)
for i in range(Z.shape[0]):
    for j in range(Z.shape[1]):
        ax.text(j, i, "鳴った" if Z[i, j] else "—", ha="center", va="center", fontsize=8, color="white" if Z[i, j] else GRAY)
ax.axhline(len(bugs) - 0.5, color=INK, lw=1)
for s in ax.spines.values(): s.set_visible(False)
ax.set_title("入れた不具合（上の16個）と無害な書き換え（下の2個）に、どのテストが鳴ったか", fontsize=11, pad=38)
save(fig, "a303_matrix.png", SRC, y=0.02)

# ---------- 図2：テストごとの、見つけた不具合の数と空振り
fig, ax = plt.subplots(figsize=(8.4, 4.2))
lab = ["T1\n関数ごと", "T2\n出力の形", "T3\n合計の照合", "T1〜T3\nのどれか", "T4 通し\n（手の24行）", "T5 通し\n（似せた500行）"]
v = [summ["T1 関数ごと"]["caught"], summ["T2 出力の形"]["caught"], summ["T3 合計の照合"]["caught"], summ["T1+T2+T3"]["caught"],
     summ["T4 通し（手で作った24行）"]["caught"], summ["T5 通し（本番に似せた500行）"]["caught"]]
fa = [summ["T1 関数ごと"]["false_alarm_on_harmless"], summ["T2 出力の形"]["false_alarm_on_harmless"], summ["T3 合計の照合"]["false_alarm_on_harmless"], None,
      summ["T4 通し（手で作った24行）"]["false_alarm_on_harmless"], summ["T5 通し（本番に似せた500行）"]["false_alarm_on_harmless"]]
b = ax.bar(lab, v, color=[GRAY, GRAY, GRAY, "#6f6e69", BLUE, ORANGE])
for i, (vv, f) in enumerate(zip(v, fa)):
    ax.text(i, vv + 0.3, f"{vv}/16" + ("" if f is None else f"\n空振り {f}/2"), ha="center", fontsize=9)
ax.set_ylim(0, 19.5); ax.set_ylabel("見つけた不具合の数（16個のうち）"); ax.set_title("テストの種類ごとに、見つけた不具合の数")
save(fig, "a303_caught.png", SRC)

# ---------- 図3：本番に似せた入力の行数と、通しテストが見つけた数
fig, ax = plt.subplots(figsize=(8, 4.2))
ax.plot(range(len(sz)), sz["mean"], color=ORANGE, marker="o", lw=2, label="本番に似せた入力を抜き出した通しテスト（30通りの平均）")
ax.fill_between(range(len(sz)), sz["min"], sz["max"], color=ORANGE, alpha=0.15, label="30通りの最小〜最大")
ax.axhline(summ["T4 通し（手で作った24行）"]["caught"], color=BLUE, lw=2, ls="--", label="手で作った24行の通しテスト")
ax.set_xticks(range(len(sz))); ax.set_xticklabels([f"{int(n):,}行" for n in sz.index]); ax.set_ylim(0, 17)
ax.set_ylabel("見つけた不具合の数（16個のうち）"); ax.set_title("入力を大きくすると、通しテストはどこまで見つけるか"); ax.legend(frameon=False, fontsize=9, loc="lower right")
save(fig, "a303_sample_size.png", SRC)

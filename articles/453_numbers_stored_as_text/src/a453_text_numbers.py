"""453 数字が文字として入った列を並べ替えると、何件が違う順番になるのか
架空の伝票（番号・枝番・金額が文字列で入る）で、文字のままの ORDER BY・MAX・BETWEEN を、数値に直した場合と比べる。"""
import json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import DATA, RES, BLUE, ORANGE, GRAY, GREEN, save

SEED, N = 453, 50000
rng = np.random.default_rng(SEED)

# ---------- 架空の伝票 ----------
cust = rng.integers(1, 2001, N)                                   # 顧客 2,000
amount = np.round(np.exp(rng.normal(8.6, 1.3, N))).astype(int).clip(1, 9_999_999)   # 金額（円）：1桁〜7桁
slip_no = rng.permutation(np.arange(1, N + 1))                    # 伝票番号 1〜50,000（そろえていない）
branch = rng.integers(1, 16, N)                                   # 枝番 1〜15
df = pd.DataFrame({"row_id": np.arange(1, N + 1), "customer": cust, "slip_no": slip_no.astype(str),
                   "slip_no_padded": [f"{x:06d}" for x in slip_no], "branch": branch.astype(str), "amount": amount.astype(str)})
df.to_csv(DATA / "slips.csv", index=False)

con = duckdb.connect()
con.execute(f"CREATE TABLE slips AS SELECT * FROM read_csv('{DATA / 'slips.csv'}', all_varchar=true)")
assert con.execute("SELECT typeof(amount), typeof(slip_no) FROM slips LIMIT 1").fetchone() == ("VARCHAR", "VARCHAR")


def moved(col, cast="BIGINT"):
    """文字のままの並び順と、数値に直した並び順で、順位が違う行の割合と、順位のずれ。"""
    q = f"""
    WITH r AS (SELECT row_id,
                      ROW_NUMBER() OVER (ORDER BY {col}, row_id) AS r_text,
                      ROW_NUMBER() OVER (ORDER BY CAST({col} AS {cast}), row_id) AS r_num
               FROM slips)
    SELECT AVG(CASE WHEN r_text <> r_num THEN 1.0 ELSE 0 END) AS moved, MEDIAN(ABS(r_text - r_num)) AS med_shift, MAX(ABS(r_text - r_num)) AS max_shift,
           CORR(r_text, r_num) AS corr FROM r"""
    return con.execute(q).fetchone()


PA, PB = np.random.default_rng(SEED + 7).integers(0, N, (2, 200000))      # 2件ずつ選ぶ20万組


def inversions(text_vals, num_vals, a=None, b=None):
    """2件を選んだとき、文字で比べた大小と数で比べた大小が逆になる割合（%）。数が同じ組は除く。"""
    a = PA if a is None else a; b = PB if b is None else b
    t = np.asarray(text_vals, dtype=object); v = np.asarray(num_vals, dtype=float)
    keep = v[a] != v[b]
    ta, tb = t[a][keep], t[b][keep]
    lt_text = np.array([x < y for x, y in zip(ta, tb)])
    return round(100 * float((lt_text != (v[a][keep] < v[b][keep])).mean()), 1)


COLS = {"slip_no": slip_no, "slip_no_padded": slip_no, "branch": branch, "amount": amount}
order_rows = []
for col, lab in (("slip_no", "伝票番号（1〜50,000、桁をそろえていない）"), ("slip_no_padded", "伝票番号（6桁にゼロ埋め）"),
                 ("branch", "枝番（1〜15）"), ("amount", "金額（2桁〜7桁）")):
    mv, med, mx, cr = moved(col)
    order_rows.append({"column": lab, "pair_reversed_pct": inversions(df[col].values, COLS[col]), "moved_pct": round(100 * mv, 1), "median_shift": int(med), "max_shift": int(mx), "rank_corr": round(cr, 3)})
order = pd.DataFrame(order_rows); order.to_csv(RES / "order_by_text_vs_number.csv", index=False)

# 並べ替えの先頭10件（金額の大きい順）
top_text = con.execute("SELECT amount FROM slips ORDER BY amount DESC, row_id LIMIT 10").df().amount.tolist()
top_num = con.execute("SELECT amount FROM slips ORDER BY CAST(amount AS BIGINT) DESC, row_id LIMIT 10").df().amount.tolist()
pd.DataFrame({"rank": range(1, 11), "text_order": top_text, "number_order": top_num}).to_csv(RES / "top10_amount.csv", index=False)

# ---------- MAX・MIN（顧客ごと） ----------
mm = con.execute("""
SELECT customer, COUNT(*) AS n, MAX(amount) AS max_text, MAX(CAST(amount AS BIGINT)) AS max_num,
       MIN(amount) AS min_text, MIN(CAST(amount AS BIGINT)) AS min_num
FROM slips GROUP BY customer""").df()
mm["max_wrong"] = mm.max_text.astype(int) != mm.max_num
mm["min_wrong"] = mm.min_text.astype(int) != mm.min_num
mm["max_ratio"] = mm.max_text.astype(int) / mm.max_num
maxmin = {"customers": int(len(mm)), "max_wrong_pct": round(100 * mm.max_wrong.mean(), 1), "min_wrong_pct": round(100 * mm.min_wrong.mean(), 1),
          "max_text_over_true_median_when_wrong": round(float(mm.max_ratio[mm.max_wrong].median()), 3),
          "all_max_text": con.execute("SELECT MAX(amount) FROM slips").fetchone()[0], "all_max_num": int(con.execute("SELECT MAX(CAST(amount AS BIGINT)) FROM slips").fetchone()[0]),
          "all_min_text": con.execute("SELECT MIN(amount) FROM slips").fetchone()[0], "all_min_num": int(con.execute("SELECT MIN(CAST(amount AS BIGINT)) FROM slips").fetchone()[0])}
# 顧客あたりの件数別
mm["nbin"] = pd.cut(mm.n, [0, 10, 20, 30, 40, 1000], labels=["〜10件", "11〜20件", "21〜30件", "31〜40件", "41件〜"])
bn = mm.groupby("nbin", observed=True).agg(customers=("n", "size"), max_wrong_pct=("max_wrong", lambda x: round(100 * x.mean(), 1)), min_wrong_pct=("min_wrong", lambda x: round(100 * x.mean(), 1))).reset_index()
bn.to_csv(RES / "max_min_by_group_size.csv", index=False)

# ---------- BETWEEN ----------
ranges = [(1000, 5000), (5000, 20000), (10000, 99999), (800, 12000), (30000, 100000), (99, 1000)]
bt = []
for lo, hi in ranges:
    t = con.execute(f"""
    SELECT SUM(CASE WHEN amount BETWEEN '{lo}' AND '{hi}' THEN 1 ELSE 0 END) AS n_text,
           SUM(CASE WHEN CAST(amount AS BIGINT) BETWEEN {lo} AND {hi} THEN 1 ELSE 0 END) AS n_num,
           SUM(CASE WHEN CAST(amount AS BIGINT) BETWEEN {lo} AND {hi} AND NOT (amount BETWEEN '{lo}' AND '{hi}') THEN 1 ELSE 0 END) AS missed,
           SUM(CASE WHEN NOT (CAST(amount AS BIGINT) BETWEEN {lo} AND {hi}) AND amount BETWEEN '{lo}' AND '{hi}' THEN 1 ELSE 0 END) AS extra
    FROM slips""").fetchone()
    bt.append({"range": f"{lo:,}〜{hi:,}円", "digits": f"{len(str(lo))}桁〜{len(str(hi))}桁", "true": int(t[1]), "text_result": int(t[0]), "missed": int(t[2]), "extra": int(t[3]),
               "missed_pct": round(100 * t[2] / t[1], 1), "extra_pct_of_result": round(100 * t[3] / max(t[0], 1), 1)})
bt = pd.DataFrame(bt); bt.to_csv(RES / "between_text_vs_number.csv", index=False)

# ---------- 桁数の混ざり方を変える（並び順・顧客ごとの MAX） ----------
mix = []
for lab, lo, hi in (("4桁だけ（1,000〜9,999）", 1000, 9999), ("3〜4桁（100〜9,999）", 100, 9999), ("3〜5桁（100〜99,999）", 100, 99999),
                    ("1〜5桁（1〜99,999）", 1, 99999), ("1〜7桁（1〜9,999,999）", 1, 9999999)):
    r = np.random.default_rng(SEED + hi % 97)
    v = np.exp(r.uniform(np.log(lo), np.log(hi + 1), 20000)).astype(int).clip(lo, hi)     # 桁ごとにほぼ同じ件数
    t = pd.DataFrame({"g": r.integers(1, 801, 20000), "v": v, "s": v.astype(str)})
    rt = t.s.rank(method="first"); rn = t.v.rank(method="first")
    order_t = np.argsort(np.argsort(t.s.values, kind="stable")); order_n = np.argsort(np.argsort(t.v.values, kind="stable"))
    g = t.groupby("g").agg(mt=("s", "max"), mn=("v", "max"))
    pa, pb = r.integers(0, 20000, (2, 100000))
    mix.append({"mix": lab, "pair_reversed_pct": inversions(t.s.values, t.v.values, pa, pb), "moved_pct": round(100 * (order_t != order_n).mean(), 1), "max_wrong_pct": round(100 * (g.mt.astype(int) != g.mn).mean(), 1),
                "rank_corr": round(float(np.corrcoef(order_t, order_n)[0, 1]), 3)})
mix = pd.DataFrame(mix); mix.to_csv(RES / "digit_mix_scenarios.csv", index=False)

# ---------- 直し方：数値に直す／ゼロ埋めして比べる（負の数・小数・カンマがあると） ----------
fix = []
vals = pd.Series(df.amount)
pad = vals.str.zfill(7)
fix.append({"data": "整数だけ（元の金額）", "method": "ゼロ埋め（7桁）して文字で比べる", "pair_reversed_pct": inversions(pad.values, amount), "not_converted": 0, "silently_changed": 0})
fix.append({"data": "整数だけ（元の金額）", "method": "整数に直す（CAST AS BIGINT）", "pair_reversed_pct": 0.0, "not_converted": 0, "silently_changed": 0})
r = np.random.default_rng(SEED + 1)
messy = vals.copy()
idx = r.choice(N, 3000, replace=False)
messy.iloc[idx[:1000]] = ["-" + x for x in messy.iloc[idx[:1000]]]                 # 返品（負の数）
messy.iloc[idx[1000:2000]] = [f"{int(x):,}" for x in messy.iloc[idx[1000:2000]]]   # カンマ入り
messy.iloc[idx[2000:]] = [x + ".5" for x in messy.iloc[idx[2000:]]]                # 小数
true_messy = messy.str.replace(",", "").astype(float)
padm = messy.str.zfill(9)
con.register("messy", pd.DataFrame({"s": messy, "truth": true_messy}))
e = con.execute("""SELECT
  SUM(CASE WHEN TRY_CAST(s AS BIGINT) IS NULL THEN 1 ELSE 0 END), SUM(CASE WHEN TRY_CAST(s AS BIGINT) <> truth THEN 1 ELSE 0 END),
  SUM(CASE WHEN TRY_CAST(s AS DOUBLE) IS NULL THEN 1 ELSE 0 END), SUM(CASE WHEN TRY_CAST(s AS DOUBLE) <> truth THEN 1 ELSE 0 END),
  SUM(CASE WHEN TRY_CAST(REPLACE(s, ',', '') AS DECIMAL(12,1)) IS NULL THEN 1 ELSE 0 END), SUM(CASE WHEN TRY_CAST(REPLACE(s, ',', '') AS DECIMAL(12,1)) <> truth THEN 1 ELSE 0 END)
  FROM messy""").fetchone()
D2 = "負の数・カンマ入り・小数が1,000件ずつ混ざる"
fix.append({"data": D2, "method": "ゼロ埋め（9桁）して文字で比べる", "pair_reversed_pct": inversions(padm.values, true_messy.values), "not_converted": 0, "silently_changed": 0})
fix.append({"data": D2, "method": "整数に直す（TRY_CAST AS BIGINT）", "pair_reversed_pct": None, "not_converted": int(e[0]), "silently_changed": int(e[1])})
fix.append({"data": D2, "method": "小数に直す（TRY_CAST AS DOUBLE）", "pair_reversed_pct": None, "not_converted": int(e[2]), "silently_changed": int(e[3])})
fix.append({"data": D2, "method": "カンマを取ってから小数に直す", "pair_reversed_pct": None, "not_converted": int(e[4]), "silently_changed": int(e[5])})
fix = pd.DataFrame(fix); fix.to_csv(RES / "fixes.csv", index=False)

digits = vals.str.len().value_counts().sort_index()
main = {"seed": SEED, "n": N, "digits_distribution": {int(k): int(v) for k, v in digits.items()}, "order": order_rows, "maxmin": maxmin,
        "between": bt.to_dict(orient="records"), "mix": mix.to_dict(orient="records"), "fixes": fix.to_dict(orient="records"),
        "top10_text": top_text, "top10_num": top_num}
json.dump(main, open(RES / "a453_main.json", "w"), ensure_ascii=False, indent=1)

# ---------- 図 ----------
SRC = "架空のデータ（作成者が乱数で作成、seed 453）。SQL は DuckDB で実行"
fig, ax = plt.subplots(figsize=(8.6, 3.8))
s = order.iloc[::-1]
ax.barh(s["column"], s.pair_reversed_pct, color=BLUE)
for i, v in enumerate(s.pair_reversed_pct):
    ax.text(v + 1, i, f"{v:.1f}%", va="center", fontsize=10)
ax.set_xlim(0, 60); ax.set_xlabel("2件を選んだとき、文字で比べた大小が数の大小と逆になる割合（%）"); ax.set_title("文字のまま比べると、大小が逆になる組の割合")
save(fig, "a453_order_moved.png", SRC)

fig, ax = plt.subplots(figsize=(8.6, 4.0))
x = np.arange(len(mix)); wd = 0.38
ax.bar(x - wd / 2, mix.pair_reversed_pct, wd, color=BLUE, label="大小が逆になる組")
ax.bar(x + wd / 2, mix.max_wrong_pct, wd, color=ORANGE, label="グループごとの MAX が違ったグループ")
for i, (a, b) in enumerate(zip(mix.pair_reversed_pct, mix.max_wrong_pct)):
    ax.text(i - wd / 2, a + 1.5, f"{a:.0f}%", ha="center", fontsize=9); ax.text(i + wd / 2, b + 1.5, f"{b:.0f}%", ha="center", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels([m.replace("（", "\n（") for m in mix.mix], fontsize=8.5); ax.set_ylim(0, 115); ax.set_ylabel("割合（%）")
ax.legend(frameon=False, fontsize=9, loc="upper left"); ax.set_title("桁数の混ざり方ごとの、大小の逆転と MAX の誤り")
save(fig, "a453_digit_mix.png", SRC)

fig, ax = plt.subplots(figsize=(8.6, 4.0))
x = np.arange(len(bt)); wd = 0.27
ax.bar(x - wd, bt["true"], wd, color=GRAY, label="本当に範囲に入る件数")
ax.bar(x, bt.missed, wd, color=ORANGE, label="文字の BETWEEN で漏れた件数")
ax.bar(x + wd, bt.extra, wd, color=BLUE, label="文字の BETWEEN で余分に入った件数")
ax.set_xticks(x); ax.set_xticklabels([f"{a}\n（{b}）" for a, b in zip(bt.range, bt.digits)], fontsize=8.5); ax.set_ylabel("件数")
ax.legend(frameon=False, fontsize=9); ax.set_title("金額の範囲を文字のまま BETWEEN で絞ったとき")
save(fig, "a453_between.png", SRC)
print(order.to_string()); print(maxmin); print(bn.to_string()); print(bt.to_string()); print(mix.to_string()); print(fix.to_string()); print(main["digits_distribution"]); print(top_text, top_num)

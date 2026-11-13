"""561 同じ人が続けて送った問い合わせを、何分以内なら1件とみなすかで、件数はどれだけ変わるのか

架空の問い合わせ窓口（2025年10〜12月、3か月）。本来の問い合わせに、次の「重複」を混ぜる：
  二重送信（ボタンの押し直し）：0〜20秒後
  自動返信が来ないための送り直し：2〜60分後
  翌日以降の催促：1〜3日後（同じ用件なので、正解では重複とする）
一方で、同じ人が別の用件を続けて送ることもある（5分〜6時間後、正解では別の件）。
同じ人の直前の問い合わせからの間隔が「幅」以内なら同じ件とみなす（直前からの間隔で区切る）。
幅を0秒〜3日で動かし、件数・取りこぼし（重複なのに別の件とした数）・まとめすぎ（別の用件なのに同じ件とした数）を数える。
「同じ分類のときだけまとめる」条件も比べる。正しい件数は、作成者が付けた用件の番号で出す。
Python と SQL（DuckDB、1スレッド）で件数が一致することを確かめる。数字は置いた仮定で決まる。
"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, LIGHT, GREEN, INK

SRC = "出典：架空の問い合わせ（作成者が乱数で作成、seed 561）"
rng = np.random.default_rng(561)
START = pd.Timestamp("2025-10-01")
DAYS = 92
NC = 6000          # 問い合わせをする人
CATS = ["注文・配送", "返品・交換", "支払い", "会員・ログイン", "商品の質問"]
CP = [0.32, 0.18, 0.14, 0.16, 0.20]

rows = []
case_id = 0
for c in range(NC):
    cid = 100000 + c
    n_case = 1 + rng.poisson(0.9)              # 1人あたりの用件の数
    for _ in range(n_case):
        # 受付時刻：日中が多い
        day = rng.integers(0, DAYS)
        hour = rng.choice(np.arange(24), p=np.r_[[0.5] * 7, [3, 5, 6, 6, 5, 6, 6, 6, 5, 5, 5, 6, 6, 5, 4], [2.5, 1.5]] / np.r_[[0.5] * 7, [3, 5, 6, 6, 5, 6, 6, 6, 5, 5, 5, 6, 6, 5, 4], [2.5, 1.5]].sum())
        t0 = START + pd.Timedelta(days=int(day), hours=int(hour), seconds=int(rng.integers(0, 3600)))
        cat = rng.choice(CATS, p=CP)
        case_id += 1
        rows.append((cid, case_id, t0, cat, "本来"))
        # 重複
        if rng.random() < 0.07:                    # 二重送信
            for _ in range(1 + (rng.random() < 0.2)):
                rows.append((cid, case_id, t0 + pd.Timedelta(seconds=float(rng.uniform(0.5, 20))), cat, "二重送信"))
        if rng.random() < 0.05:                    # 送り直し
            rows.append((cid, case_id, t0 + pd.Timedelta(minutes=float(rng.uniform(2, 60))), cat, "送り直し"))
        if rng.random() < 0.03:                    # 翌日以降の催促
            rows.append((cid, case_id, t0 + pd.Timedelta(hours=float(rng.uniform(24, 72))), cat, "催促"))
        # 別の用件を続けて送る
        if rng.random() < 0.04:
            case_id += 1
            cat2 = cat if rng.random() < 0.35 else rng.choice([x for x in CATS if x != cat])
            rows.append((cid, case_id, t0 + pd.Timedelta(minutes=float(np.exp(rng.uniform(np.log(5), np.log(360))))), cat2, "別の用件"))
df = pd.DataFrame(rows, columns=["customer_id", "true_case", "received_at", "category", "kind"])
df = df.sort_values(["received_at", "customer_id"]).reset_index(drop=True)
df["received_at"] = df.received_at.dt.floor("s")
df.insert(0, "inquiry_id", np.arange(1, len(df) + 1))
df[["inquiry_id", "customer_id", "received_at", "category"]].to_csv(DATA / "inquiries.csv", index=False)
df[["inquiry_id", "true_case", "kind"]].to_csv(DATA / "inquiries_true_case.csv", index=False)

TRUE_N = df.true_case.nunique()
s = df.sort_values(["customer_id", "received_at", "inquiry_id"]).copy()
s["prev_t"] = s.groupby("customer_id").received_at.shift()
s["prev_case"] = s.groupby("customer_id").true_case.shift()
s["prev_cat"] = s.groupby("customer_id").category.shift()
s["gap"] = (s.received_at - s.prev_t).dt.total_seconds()
s["true_same"] = s.true_case == s.prev_case          # 直前と同じ用件か（正解）

WINDOWS = [("0秒", 0), ("30秒", 30), ("1分", 60), ("5分", 300), ("10分", 600), ("30分", 1800), ("1時間", 3600),
           ("3時間", 10800), ("24時間", 86400), ("3日", 259200)]


def evaluate(w, same_cat):
    merge = s.gap.notna() & (s.gap <= w)
    if same_cat:
        merge &= s.category == s.prev_cat
    # 直前とつなぐかどうかの判定の正誤（直前との組で数える）
    missed = int((~merge & s.true_same).sum())          # 重複なのに別の件
    over = int((merge & ~s.true_same & s.gap.notna()).sum())  # 別の用件なのに同じ件
    n = int(len(s) - merge.sum())
    return n, missed, over


res = []
for lab, w in WINDOWS:
    for sc in (False, True):
        n, m, o = evaluate(w, sc)
        res.append({"window": lab, "seconds": w, "same_category": sc, "count": n, "diff_pct": round(100 * (n / TRUE_N - 1), 2),
                    "missed": m, "over_merged": o})
R = pd.DataFrame(res)
R.to_csv(RES / "by_window.csv", index=False)

# SQL（DuckDB）で同じ判定：幅10分・分類を問わない／同じ分類だけ
con = duckdb.connect()
con.execute("SET threads=1")
con.execute(f"CREATE TABLE inquiries AS SELECT * FROM read_csv_auto('{DATA / 'inquiries.csv'}', timestampformat='%Y-%m-%d %H:%M:%S')")
sql = (SQL / "02_dedup_duckdb.sql").read_text()
chk = {}
for lab, w in WINDOWS:
    for sc in (0, 1):
        v = con.execute(sql.replace(":window_sec", str(w)).replace(":same_cat", str(sc))).fetchone()[0]
        py = int(R[(R.seconds == w) & (R.same_category == bool(sc))]["count"].iloc[0])
        assert v == py, (lab, sc, v, py)
        chk[f"{lab}_{sc}"] = v

kinds = df.kind.value_counts().to_dict()
gaps_dup = s[s.true_same].gap
gaps_new = s[~s.true_same & s.gap.notna()].gap
best = R.loc[(R.missed + R.over_merged).idxmin()]
summary = {"rows": len(df), "customers_with_inquiry": int(df.customer_id.nunique()), "true_cases": TRUE_N, "kinds": kinds,
           "pairs_with_prev": int(s.gap.notna().sum()), "dup_pairs": int(s.true_same.sum()), "new_pairs": int(len(gaps_new)),
           "new_within_1h": int((gaps_new <= 3600).sum()), "new_within_10min": int((gaps_new <= 600).sum()),
           "dup_over_1h": int((gaps_dup > 3600).sum()),
           "best_window_by_errors": {k: (v.item() if hasattr(v, "item") else v) for k, v in best.to_dict().items()},
           "sql_python_match": True}
json.dump(summary, open(RES / "a561_main.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(summary, ensure_ascii=False))
print(R.to_string())

# 図1：幅ごとの件数（正しい件数との差）
fig, ax = plt.subplots(figsize=(8, 4.2))
x = np.arange(len(WINDOWS))
for sc, col, lab in ((False, BLUE, "分類を問わずまとめる"), (True, ORANGE, "同じ分類のときだけまとめる")):
    y = R[R.same_category == sc].diff_pct.values
    ax.plot(x, y, marker="o", color=col, label=lab)
    for xi, yi in zip(x, y):
        if sc is False:
            ax.annotate(f"{yi:+.1f}", (xi, yi), textcoords="offset points", xytext=(0, 7), ha="center", fontsize=8, color=col)
ax.axhline(0, color=INK, lw=0.8)
ax.set_xticks(x, [w[0] for w in WINDOWS])
ax.set_ylabel("正しい件数との差（%）")
ax.set_xlabel("直前の問い合わせから、この幅以内なら同じ件とみなす")
ax.set_title(f"幅を変えると件数はどれだけ変わるか（正しい件数 {TRUE_N:,}件）", loc="left")
ax.legend(frameon=False, fontsize=9)
save(fig, "a561_count.png", SRC)

# 図2：取りこぼしとまとめすぎ
fig, axs = plt.subplots(1, 2, figsize=(9.5, 4), sharey=True)
for ax, sc, t in zip(axs, (False, True), ("分類を問わずまとめる", "同じ分類のときだけまとめる")):
    q = R[R.same_category == sc]
    ax.bar(x - 0.2, q.missed, 0.4, color=ORANGE, label="取りこぼし（重複なのに別の件）")
    ax.bar(x + 0.2, q.over_merged, 0.4, color=BLUE, label="まとめすぎ（別の用件なのに同じ件）")
    ax.set_xticks(x, [w[0] for w in WINDOWS], rotation=45, fontsize=8.5)
    ax.set_title(t, loc="left", fontsize=11)
axs[0].set_ylabel("件数")
axs[0].legend(frameon=False, fontsize=8.5)
fig.suptitle("幅を広げると取りこぼしは減り、まとめすぎが増える", x=0.01, ha="left", fontsize=13)
save(fig, "a561_errors.png", SRC)

# 図3：同じ人の直前の問い合わせからの間隔
fig, ax = plt.subplots(figsize=(8, 4))
bins = np.logspace(np.log10(0.5), np.log10(86400 * 92), 60)
ax.hist(gaps_dup, bins=bins, color=ORANGE, alpha=0.8, label=f"同じ用件（重複）{len(gaps_dup):,}組")
ax.hist(gaps_new, bins=bins, color=BLUE, alpha=0.6, label=f"別の用件 {len(gaps_new):,}組")
ax.set_xscale("log")
for lab, w in (("1分", 60), ("10分", 600), ("1時間", 3600), ("24時間", 86400)):
    ax.axvline(w, color=GRAY, lw=0.8, ls="--")
    ax.text(w, ax.get_ylim()[1] * 0.95, lab, fontsize=8, color=GRAY, ha="left")
ax.set_xlabel("同じ人の直前の問い合わせからの間隔（秒、対数目盛）")
ax.set_ylabel("組の数")
ax.set_title("重複は数秒〜1時間と1〜3日に、別の用件は数分以降に広がる", loc="left", fontsize=12)
ax.legend(frameon=False, fontsize=9)
save(fig, "a561_gaps.png", SRC)

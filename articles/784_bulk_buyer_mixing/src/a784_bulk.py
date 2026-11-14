"""784 法人のまとめ買いを混ぜたまま客単価を見ると、個人の客単価はどれだけ高く見えるのか

架空のレシート（2025年の12か月、月に約3,000枚）。ほとんどは個人の買い物（平均約3,000円）。
一部（月に0〜60枚、月によって大きく違う）が法人のまとめ買いで、1枚が数万〜数十万円。レシートには法人かどうかの印がある。
月ごとの客単価を、全体の平均・法人を除いた平均・中央値・上位1%の値で頭打ちにした平均の4通りで出し、個人の客単価とのずれと、月ごとの振れを比べる。
DuckDB（1スレッド）と pandas で一致を確かめる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import duckdb
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, GREEN

SRC = "出典：架空のレシート（作成者が乱数で作成、seed 784）"
rng = np.random.default_rng(784)
BIZ = [5, 8, 60, 12, 6, 30, 9, 4, 45, 10, 7, 55]          # 月ごとの法人のレシートの枚数（年度末・季節で多い月がある）
rows = []
for m in range(1, 13):
    n = int(rng.normal(3000, 120))
    p = np.round(rng.lognormal(7.85, .55, n), -1)
    b = np.round(rng.lognormal(10.8, .7, BIZ[m - 1]), -1)
    rows.append(pd.DataFrame({"month": f"2025-{m:02d}", "amount": np.r_[p, b].astype(int), "is_business": np.r_[np.zeros(n, int), np.ones(len(b), int)]}))
R_ = pd.concat(rows, ignore_index=True)
DATA.mkdir(exist_ok=True); R_.to_csv(DATA / "receipts.csv", index=False)
con = duckdb.connect(); con.execute("SET threads=1"); con.register("receipts", R_)
q = "\n".join(l for l in (SQL / "02_spend_duckdb.sql").read_text(encoding="utf-8").splitlines() if not l.strip().startswith("--")).strip().rstrip(";")
Q = con.execute(q).df()
g = R_.groupby("month")
P = pd.DataFrame({"month": sorted(R_.month.unique())})
P["mean_all"] = g.amount.mean().values
P["mean_personal"] = R_[R_.is_business == 0].groupby("month").amount.mean().values
P["median_all"] = g.amount.median().values
P["mean_capped"] = g.amount.apply(lambda s: np.minimum(s, s.quantile(.99)).mean()).values
P["n_business"] = g.is_business.sum().values; P["n"] = g.size().values
P["business_amount_share"] = (R_[R_.is_business == 1].groupby("month").amount.sum() / g.amount.sum()).values
for c in ["mean_all", "mean_personal", "median_all", "mean_capped"]:
    assert np.allclose(P[c].to_numpy(), Q[c].to_numpy(), rtol=1e-9)
P.to_csv(RES / "by_month.csv", index=False)
gap = lambda c: (P[c] / P.mean_personal - 1)
cv = lambda c: float(P[c].std() / P[c].mean())
out = {"receipts": len(R_), "business_receipts": int(R_.is_business.sum()), "business_receipt_share": float(R_.is_business.mean()),
       "business_amount_share": float(R_[R_.is_business == 1].amount.sum() / R_.amount.sum()),
       "personal_mean_year": float(R_[R_.is_business == 0].amount.mean()),
       "gap_all_mean": float(gap("mean_all").mean()), "gap_all_max": float(gap("mean_all").max()), "gap_all_max_month": str(P.month[gap("mean_all").idxmax()]),
       "gap_all_min": float(gap("mean_all").min()),
       "gap_capped_mean": float(gap("mean_capped").mean()), "gap_capped_max": float(gap("mean_capped").max()),
       "median_vs_personal_mean": float((P.median_all / P.mean_personal - 1).mean()),
       "cv_all": cv("mean_all"), "cv_personal": cv("mean_personal"), "cv_capped": cv("mean_capped"), "cv_median": cv("median_all"),
       "duckdb_version": duckdb.__version__}
json.dump(out, open(RES / "a784_main.json", "w"), ensure_ascii=False, indent=1)

x = np.arange(12); lab = [m[5:] + "月" for m in P.month]
# 図1：月ごとの客単価
fig, ax = plt.subplots(figsize=(10, 4.6))
for c, l, col, mk in [("mean_all", "全体の平均", ORANGE, "o"), ("mean_capped", "上位1%で頭打ち", GREEN, "^"), ("mean_personal", "法人を除いた平均（個人）", BLUE, "s"), ("median_all", "中央値", GRAY, "d")]:
    ax.plot(x, P[c], marker=mk, color=col, label=l)
ax.set_xticks(x); ax.set_xticklabels(lab); ax.set_ylabel("客単価（円）"); ax.legend(frameon=False, ncol=2, fontsize=9)
ax.set_title("法人のまとめ買いが多い月だけ、全体の平均が跳ね上がる")
save(fig, "a784_monthly.png", SRC)
# 図2：法人の枚数とずれ
fig, ax = plt.subplots(figsize=(9, 4.6))
ax.scatter(P.n_business, gap("mean_all") * 100, color=ORANGE, s=40, label="全体の平均")
ax.scatter(P.n_business, gap("mean_capped") * 100, color=GREEN, s=40, marker="^", label="上位1%で頭打ち")
for a, b, l in zip(P.n_business, gap("mean_all") * 100, lab): ax.text(a + .8, b, l, fontsize=8)
ax.axhline(0, color=GRAY, lw=1)
ax.set_xlabel("その月の法人のレシートの枚数（約3,000枚のうち）"); ax.set_ylabel("個人の客単価からのずれ（%）"); ax.legend(frameon=False)
ax.set_title("ずれは、法人のレシートの枚数でほぼ決まる")
save(fig, "a784_business.png", SRC)
# 図3：月ごとの振れ（変動係数）
fig, ax = plt.subplots(figsize=(9, 4.6))
lab3 = ["全体の平均", "上位1%で頭打ち", "法人を除いた平均", "中央値"]
v = [out["cv_all"] * 100, out["cv_capped"] * 100, out["cv_personal"] * 100, out["cv_median"] * 100]
b = ax.bar(lab3, v, color=[ORANGE, GREEN, BLUE, GRAY])
for bb, vv in zip(b, v): ax.text(bb.get_x() + bb.get_width() / 2, vv + .3, f"{vv:.1f}%", ha="center")
ax.set_ylabel("12か月の客単価の変動係数（%）"); ax.set_title("全体の平均は、月ごとの振れが個人の客単価の数倍になる")
save(fig, "a784_cv.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))

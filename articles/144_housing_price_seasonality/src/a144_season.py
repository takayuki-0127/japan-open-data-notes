"""住宅の価格指数は何月に高く出るのか：原系列の季節性"""
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from statsmodels.tsa.seasonal import STL
from common import load, FIG, RES, C, CATS

idx, tx = load()
idx["date"] = pd.to_datetime(idx["month"])
END = "2024-12"   # 季節性の推定は2025年の速報分（サンプルがまだ少ない月）を除く
M = range(1, 13)


def stl_season(s):
    s = s.dropna()
    r = STL(np.log(s), period=12, robust=True, seasonal=13).fit()
    seas = pd.Series(np.exp(r.seasonal) * 100 - 100, index=s.index)
    resid_sd = float(np.std(r.resid)) * 100
    return seas, resid_sd


rows, prof = [], []
for (area, cat), g in idx.groupby(["area", "category"]):
    g = g.set_index("date").sort_index()
    g = g[g.index <= END]
    seas, rsd = stl_season(g["index_raw"])
    off = (g["index_raw"] / g["index_sa"] * 100 - 100).dropna()  # 公表の季節調整値との差
    for m in M:
        sm = seas[seas.index.month == m]
        om = off[off.index.month == m]
        prof.append({"area": area, "category": cat, "month": m,
                     "stl_pct": sm.mean(), "stl_early": sm[sm.index.year <= 2016].mean(),
                     "stl_late": sm[sm.index.year >= 2017].mean(), "official_pct": om.mean()})
    p = pd.DataFrame([x for x in prof if x["area"] == area and x["category"] == cat])
    rows.append({"area": area, "category": cat,
                 "peak_month": int(p.loc[p.stl_pct.idxmax(), "month"]), "peak_pct": p.stl_pct.max(),
                 "low_month": int(p.loc[p.stl_pct.idxmin(), "month"]), "low_pct": p.stl_pct.min(),
                 "range_pct": p.stl_pct.max() - p.stl_pct.min(), "resid_sd_pct": rsd,
                 "official_range_pct": p.official_pct.max() - p.official_pct.min(),
                 "early_late_corr": np.corrcoef(p.stl_early, p.stl_late)[0, 1]})
prof = pd.DataFrame(prof)
summ = pd.DataFrame(rows)
prof.round(3).to_csv(os.path.join(RES, "a144_seasonal_profile.csv"), index=False)
summ.round(3).to_csv(os.path.join(RES, "a144_seasonal_summary.csv"), index=False)
print(summ.round(2).to_string())

# 1) 全国4種類の月別の季節成分
fig, ax = plt.subplots(figsize=(8.2, 4.4))
nat = prof[prof.area == "全国"]
for i, c in enumerate(CATS):
    g = nat[nat.category == c]
    ax.plot(g.month, g.stl_pct, marker="o", color=C[i], lw=2, label=c)
ax.axhline(0, color="#333", lw=0.8)
ax.set_xticks(list(M))
ax.set_xticklabels([f"{m}月" for m in M])
ax.set_ylabel("季節成分（%、年平均＝0）")
ax.set_title("全国の不動産価格指数（住宅）の季節成分（2008年4月〜2024年12月）")
ax.legend(frameon=False, fontsize=9, ncol=2)
fig.tight_layout()
fig.savefig(os.path.join(FIG, "a144_profile.png"))

# 2) 地域別：マンションと住宅地の季節の幅と、ふだんの振れ
sub = summ[summ.category.isin(["マンション（区分所有）", "戸建住宅", "住宅地"])].copy()
areas = ["全国", "南関東圏", "名古屋圏", "京阪神圏", "東京都"]
fig, axes = plt.subplots(1, 3, figsize=(10.5, 4), sharey=True)
for ax, c in zip(axes, ["住宅地", "戸建住宅", "マンション（区分所有）"]):
    g = sub[sub.category == c].set_index("area").loc[areas]
    x = np.arange(len(areas))
    ax.bar(x - 0.2, g.range_pct, 0.4, color=C[0], label="季節の幅（最大月−最小月）")
    ax.bar(x + 0.2, g.resid_sd_pct, 0.4, color=C[5], label="不規則な振れ（標準偏差）")
    ax.set_xticks(x)
    ax.set_xticklabels(areas, rotation=45, fontsize=9)
    ax.set_title(c, fontsize=11)
axes[0].set_ylabel("%")
axes[0].legend(frameon=False, fontsize=8, loc="upper left")
fig.suptitle("季節の動きと不規則な振れの大きさ（2008〜2024年）", fontweight="bold")
fig.tight_layout()
fig.savefig(os.path.join(FIG, "a144_area.png"))

# 3) 取引件数の季節性
tx["date"] = pd.to_datetime(tx["month"])
trow = []
fig, ax = plt.subplots(figsize=(8.2, 4.2))
for i, (c, g) in enumerate(tx.groupby("category")):
    s = g.set_index("date")["transactions"].sort_index()
    s = s[s.index <= END]
    seas, rsd = stl_season(s)
    pm = seas.groupby(seas.index.month).mean()
    for m in M:
        trow.append({"category": c, "month": m, "stl_pct": pm[m]})
    ax.plot(pm.index, pm.values, marker="o", color={"戸建住宅": C[2], "マンション（区分所有）": C[3]}[c], lw=2, label=f"{c}の取引件数")
ax.axhline(0, color="#333", lw=0.8)
ax.set_xticks(list(M))
ax.set_xticklabels([f"{m}月" for m in M])
ax.set_ylabel("季節成分（%、年平均＝0）")
ax.set_title("取引件数（移転登記ベース）の季節成分（全国、2008年4月〜2024年12月）")
ax.legend(frameon=False, fontsize=9)
fig.tight_layout()
fig.savefig(os.path.join(FIG, "a144_transactions.png"))
tp = pd.DataFrame(trow)
tp.round(3).to_csv(os.path.join(RES, "a144_transactions_profile.csv"), index=False)
print(tp.pivot(index="month", columns="category", values="stl_pct").round(1).to_string())
print(nat.pivot(index="month", columns="category", values="stl_pct").round(2).to_string())
print(nat.pivot(index="month", columns="category", values="official_pct").round(2).to_string())

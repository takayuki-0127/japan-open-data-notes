"""A154 最低賃金の地域差は縮まったのか（地域別最低賃金 平成14〜令和8年度）

手法：47都道府県の地域別最低賃金（時間額）の、変動係数（標準偏差÷平均）・ジニ係数・最高/最低の比・最高−最低の差を年度ごとに計算。
さらに、2016→2026年度の引上げ率を2016年度の水準と比べる（低い県ほど大きく上がったか）。都道府県は人数の重みをつけない。
"""
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import load, save, RES, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

d = load("minimum_wage_2002_2026.csv")
P = d[d.pref != "全国加重平均"].set_index("pref")
nat = d[d.pref == "全国加重平均"].iloc[0]
Y = [str(y) for y in range(2002, 2027)]
W = P[Y].astype(float)


def gini(x):
    x = np.sort(np.asarray(x, float)); n = len(x)
    return (2 * np.arange(1, n + 1) - n - 1).dot(x) / (n * x.sum())


rows = []
for y in Y:
    x = W[y]
    rows.append({"year": int(y), "mean": round(x.mean(), 1), "median": x.median(), "max": x.max(), "min": x.min(),
                 "max_pref": x.idxmax(), "min_pref": "・".join(x[x == x.min()].index),
                 "n_min": int((x == x.min()).sum()),
                 "ratio": round(x.max() / x.min(), 4), "gap": x.max() - x.min(),
                 "cv": round(x.std(ddof=0) / x.mean(), 4), "gini": round(gini(x), 4),
                 "weighted_avg": float(nat[y])})
t = pd.DataFrame(rows)
t.to_csv(RES / "a154_inequality.csv", index=False)

g = pd.DataFrame({"w2016": W["2016"], "w2026": W["2026"], "w2002": W["2002"]})
g["up16_26"] = (g.w2026 / g.w2016 - 1) * 100
g["up02_16"] = (g.w2016 / g.w2002 - 1) * 100
g["yen16_26"] = g.w2026 - g.w2016
g = g.round(2)
g.to_csv(RES / "a154_pref_growth.csv")
r1 = np.corrcoef(np.log(g.w2016), g.up16_26)[0, 1]
r0 = np.corrcoef(np.log(g.w2002), g.up02_16)[0, 1]

# ---- 図1：変動係数とジニ係数、最高/最低の比 ----
fig, ax = plt.subplots(1, 2, figsize=(10.6, 4.4))
ax[0].plot(t.year, t.cv * 100, color=BLUE, lw=2, label="変動係数")
ax[0].plot(t.year, t.gini * 100, color=ORANGE, lw=2, label="ジニ係数")
for col, c in (("cv", BLUE), ("gini", ORANGE)):
    for yy in (2002, 2009, 2026):
        v = t.loc[t.year == yy, col].iloc[0] * 100
        ax[0].annotate(f"{v:.2f}", (yy, v), xytext=(0, 6), textcoords="offset points", ha="center", fontsize=8.5, color=c)
ax[0].set_title("ばらつき（×100）"); ax[0].legend(frameon=False); ax[0].set_ylim(0, None)
ax[1].plot(t.year, t.ratio, color=INK, lw=2)
for yy in (2002, 2009, 2014, 2026):
    v = t.loc[t.year == yy, "ratio"].iloc[0]
    ax[1].annotate(f"{v:.3f}", (yy, v), xytext=(0, 6), textcoords="offset points", ha="center", fontsize=8.5)
ax[1].set_title("最高額÷最低額"); ax[1].set_ylim(1.15, 1.33)
for a in ax:
    a.set_xlabel("年度"); a.grid(axis="y", color="#eee")
fig.suptitle("地域別最低賃金の都道府県間のばらつき（2002〜2026年度）", y=1.02)
save(fig, "a154_ratio.png")

# ---- 図2：最高・最低・中央値と差額 ----
fig, ax = plt.subplots(figsize=(8.6, 4.8))
ax.fill_between(t.year, t["min"], t["max"], color=LIGHT, alpha=.5, label="最高〜最低の幅")
ax.plot(t.year, t["max"], color=BLUE, lw=2, label="最高")
ax.plot(t.year, t["median"], color=GRAY, lw=1.6, ls="--", label="中央値")
ax.plot(t.year, t["min"], color=ORANGE, lw=2, label="最低")
for yy in (2002, 2014, 2026):
    r = t[t.year == yy].iloc[0]
    ax.annotate(f"差 {int(r.gap)}円", (yy, (r["max"] + r["min"]) / 2), ha="center", fontsize=9,
                xytext=(0 if yy != 2026 else -18, 0), textcoords="offset points")
ax.set_ylabel("時間額（円）"); ax.set_xlabel("年度")
ax.set_title("最低賃金の最高・最低と差額（円）")
ax.legend(frameon=False, loc="upper left")
save(fig, "a154_gap.png")

# ---- 図3：2016年度の水準と、その後10年の引上げ率 ----
fig, ax = plt.subplots(figsize=(7.8, 5.4))
ax.scatter(g.w2016, g.up16_26, color=GREEN, s=30)
for p_, r in g.iterrows():
    if p_ in ("東京", "神奈川", "大阪", "北海道", "愛知", "徳島"):
        ax.annotate(p_, (r.w2016, r.up16_26), xytext=(-30 if p_=="神奈川" else 5, 6 if p_=="神奈川" else -3), textcoords="offset points", fontsize=8.5)
b = np.polyfit(g.w2016, g.up16_26, 1)
xs = np.linspace(g.w2016.min(), g.w2016.max(), 10)
ax.plot(xs, np.polyval(b, xs), color=GRAY, lw=1, ls="--")
ax.set_xlabel("2016年度の最低賃金（円）"); ax.set_ylabel("2016→2026年度の引上げ率（%）")
ax.set_title(f"低い県ほど大きく上がった（相関係数 {r1:.2f}）")
save(fig, "a154_converge.png")

lines = []
for yy in (2002, 2006, 2009, 2014, 2016, 2019, 2022, 2023, 2024, 2025, 2026):
    r = t[t.year == yy].iloc[0]
    lines.append(f"{yy}: mean {r['mean']} max {r['max']:.0f}({r.max_pref}) min {r['min']:.0f}(n={r.n_min}) ratio {r.ratio:.3f} gap {r.gap:.0f} cv {r.cv*100:.2f} gini {r.gini*100:.2f} wavg {r.weighted_avg}")
lines.append(f"ratio max year {int(t.loc[t.ratio.idxmax(),'year'])} {t.ratio.max():.3f}; gap max year {int(t.loc[t.gap.idxmax(),'year'])} {t.gap.max():.0f}")
lines.append(f"r(log w2016, up16_26) {r1:.2f}; r(log w2002, up02_16) {r0:.2f}")
lines.append("up16_26 top: " + ", ".join(f"{p} {v:.1f}%" for p, v in g.up16_26.nlargest(5).items()))
lines.append("up16_26 bottom: " + ", ".join(f"{p} {v:.1f}%" for p, v in g.up16_26.nsmallest(5).items()))
lines.append(f"2026 >=1100: {(W['2026']>=1100).sum()} ; 2026 min list: {', '.join(W['2026'][W['2026']==W['2026'].min()].index)}")
lines.append(f"2025 eff after 2025-12-31: {(P.eff2025>'2025-12-31').sum()} ; 2026 eff in Nov/Dec: {(P.eff2026>='2026-11-01').sum()}")
(RES / "a154_summary.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))

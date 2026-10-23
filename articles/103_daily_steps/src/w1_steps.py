"""W1：1日の歩数は減ったか（性・年齢階級別 2003〜2024年、都道府県別 2012・2016・2024年）"""
import numpy as np, pandas as pd, statsmodels.api as sm
import matplotlib.pyplot as plt
from common import *

s = load_steps()
s.to_csv(RES / "w1_steps_by_sex_age.csv", index=False, encoding="utf-8-sig")
adj = s[s.age == "adj"].pivot(index="year", columns="sex", values="steps")

# --- 年齢調整値のトレンド（2003〜2019年、2003〜2023年）
rows = []
for sex in ["male", "female"]:
    for y0, y1 in [(2003, 2019), (2003, 2023)]:
        z = adj[sex].loc[y0:y1].dropna()
        X = sm.add_constant(z.index.values - 2003)
        m = sm.OLS(z.values, X).fit(cov_type="HAC", cov_kwds={"maxlags": 2})
        rows.append((sex, f"{y0}-{y1}", len(z), m.params[1] * 10, m.bse[1] * 10))
trend = pd.DataFrame(rows, columns=["sex", "period", "n_years", "slope_per10y", "se"])
trend.to_csv(RES / "w1_trend_adj.csv", index=False, encoding="utf-8-sig")
print(trend.round(1))

# --- 期間平均で年齢階級ごとに比べる
per = {"2003-05": (2003, 2005), "2017-19": (2017, 2019), "2022-23": (2022, 2023)}
g = s[s.age.isin(AGES)]
tab = []
for sex in ["male", "female"]:
    for a in AGES:
        z = g[(g.sex == sex) & (g.age == a)].set_index("year").steps
        rec = {"sex": sex, "age": a}
        for k, (y0, y1) in per.items():
            rec[k] = z.loc[y0:y1].mean()
        rec["2024"] = z.get(2024, np.nan)
        tab.append(rec)
tab = pd.DataFrame(tab)
tab["chg_03_19"] = tab["2017-19"] - tab["2003-05"]
tab["chg_03_23"] = tab["2022-23"] - tab["2003-05"]
tab.to_csv(RES / "w1_age_periods.csv", index=False, encoding="utf-8-sig")
print(tab.round(0).to_string())
print(adj.round(0).to_string())

# --- 図1：年齢調整値の推移
fig, ax = plt.subplots(figsize=(8.4, 4.6))
for sex, c, lab in [("male", BLUE, "男性"), ("female", ORANGE, "女性")]:
    z = adj[sex].dropna()
    for seg in [z.loc[:2019], z.loc[2022:]]:
        ax.plot(seg.index, seg.values, "-o", color=c, ms=3.5, lw=2)
    ax.text(2023.3, z.loc[2023], f"{lab} {z.loc[2023]:,.0f}歩", color=c, va="center", fontsize=10)
    ax.text(2002.7, z.loc[2003], f"{z.loc[2003]:,.0f}", color=c, va="center", ha="right", fontsize=9)
    raw24 = s[(s.year == 2024) & (s.sex == sex) & (s.age == "total")].steps.iloc[0]
    ax.plot([2024], [raw24], marker="D", mfc="white", mec=c, ms=6, ls="none")
ax.axvspan(2019.5, 2021.5, color="#eeeeee")
ax.text(2020.5, 5700, "2020・21年は\n調査なし", ha="center", fontsize=8.5, color="#555")
ax.annotate("◇2024年は集計方法が変わった\n（歩数計を1日着けなかった人を除外）。\n年齢調整前の平均で、前の年とは比べられない", xy=(2023.8, 7700), xytext=(2009.5, 7800),
            fontsize=8.5, color="#555", va="center", arrowprops=dict(arrowstyle="-", color="#999"))
ax.set_xlim(2001.5, 2026.5); ax.set_ylim(5600, 8000)
ax.set_ylabel("1日の歩数（20歳以上、年齢調整値）")
ax.set_title("1日の歩数（年齢調整値）の推移", loc="left")
note(fig)
fig.savefig(FIG / "w1_trend.png"); plt.close(fig)

# --- 図2：年齢階級別
fig, axes = plt.subplots(1, 2, figsize=(10, 4.4), sharey=True)
for ax, sex, lab in [(axes[0], "male", "男性"), (axes[1], "female", "女性")]:
    labs = []
    for a, c in zip(AGES, AGE_COLORS):
        z = g[(g.sex == sex) & (g.age == a)].set_index("year").steps
        seg = z.loc[:2019]
        ax.plot(seg.index, seg.rolling(3, center=True, min_periods=1).mean(), color=c, lw=2)
        v = z.loc[2022:2023].mean()
        ax.plot([2022.5], [v], "o", color=c, ms=6)
        labs.append([v, a, c])
    labs.sort()
    for k in range(1, len(labs)):
        if labs[k][0] - labs[k - 1][0] < 240:
            labs[k][0] = labs[k - 1][0] + 240
    for v, a, c in labs:
        ax.text(2023.5, v, a.replace("70+", "70歳以上").replace("-", "〜") + ("" if a == "70+" else "歳"), color=c, fontsize=8.5, va="center")
    ax.axvspan(2019.5, 2021.5, color="#eeeeee")
    ax.set_title(lab, loc="left"); ax.set_xlim(2002, 2027)
axes[0].set_ylabel("1日の歩数（3年移動平均。●は2022〜23年の平均）")
fig.suptitle("年齢階級別の1日の歩数（2003〜2023年）", x=0.02, ha="left", fontsize=13)
note(fig)
fig.savefig(FIG / "w1_age.png"); plt.close(fig)

# --- 都道府県：差は誤差より大きいか
p = load_step_pref()
p.to_csv(RES / "w1_pref_steps.csv", index=False, encoding="utf-8-sig")
out = []
for (y, sex), d in p.groupby(["year", "sex"]):
    nat = d[d.pref == "全国"].steps.iloc[0]
    d = d[d.pref != "全国"].copy()
    d["se"] = (d.hi - d.lo) / 3.92
    q = (((d.steps - nat) / d.se) ** 2).sum()
    mx, mn = d.loc[d.steps.idxmax()], d.loc[d.steps.idxmin()]
    out.append((y, sex, len(d), nat, d.steps.std(), d.se.median(), q, len(d) - 1, (d.lo > nat).sum(), (d.hi < nat).sum(),
                mx.pref, mx.steps, mn.pref, mn.steps))
pq = pd.DataFrame(out, columns=["year", "sex", "n_pref", "national", "sd_between", "median_se", "Q", "df",
                                "n_above_ci", "n_below_ci", "max_pref", "max_steps", "min_pref", "min_steps"])
w = p[p.pref != "全国"].pivot_table(index=["pref", "sex"], columns="year", values="steps")
cors = {sex: w.xs(sex, level="sex").corr().round(2) for sex in ["male", "female"]}
for sex in cors:
    for a, b in [(2012, 2016), (2016, 2024), (2012, 2024)]:
        pq.loc[(pq.sex == sex) & (pq.year == b), f"corr_with_{a}"] = cors[sex].loc[a, b]
pq.to_csv(RES / "w1_pref_summary.csv", index=False, encoding="utf-8-sig")
print(pq.round(2).to_string())

fig, axes = plt.subplots(1, 2, figsize=(10, 4.6))
for ax, sex, lab in [(axes[0], "male", "男性"), (axes[1], "female", "女性")]:
    ww = w.xs(sex, level="sex").dropna(subset=[2012, 2016])
    ax.scatter(ww[2012], ww[2016], s=18, color=BLUE if sex == "male" else ORANGE)
    lo, hi = ww[[2012, 2016]].min().min() - 200, ww[[2012, 2016]].max().max() + 200
    ax.plot([lo, hi], [lo, hi], color=GRAY, lw=1, ls="--")
    for nm in ww[2016].nlargest(2).index.tolist() + ww[2016].nsmallest(2).index.tolist():
        ax.annotate(nm, (ww.loc[nm, 2012], ww.loc[nm, 2016]), fontsize=8, xytext=(3, 3), textcoords="offset points")
    r = cors[sex].loc[2012, 2016]
    ax.set_title(f"{lab}（20〜64歳）　相関 {r:.2f}", loc="left")
    ax.set_xlabel("2012年の平均歩数（年齢調整）")
axes[0].set_ylabel("2016年の平均歩数（年齢調整）")
fig.suptitle("都道府県の歩数：2012年に多かった県は2016年も多いか", x=0.02, y=1.03, ha="left", fontsize=13)
note(fig, SOURCE + "　※点線は2012年と2016年が同じ値の線。2016年は熊本県を除く")
fig.savefig(FIG / "w1_pref.png"); plt.close(fig)

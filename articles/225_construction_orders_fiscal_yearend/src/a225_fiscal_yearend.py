"""225 建設工事の受注は、年度末に偏っているのか（大手50社調査、2011年1月〜2026年8月、STL分解）"""
from common import *
from statsmodels.tsa.seasonal import STL
from scipy.stats import linregress

d = load()
full = d[(d.fy >= 2011) & (d.fy <= 2025)]          # 2011年度〜2025年度（12か月そろう年度）

# 1) STL分解（対数、周期12、ロバスト）
res = {}
for c in COLS:
    s = np.log(d[c].clip(lower=1))
    st = STL(s, period=12, robust=True, seasonal=13).fit()
    res[c] = st
    out = pd.DataFrame({"obs": d[c], "trend": np.exp(st.trend), "seasonal_factor": np.exp(st.seasonal), "resid": st.resid})
    out.round(4).to_csv(RES / f"stl_{c}.csv")
sf = pd.DataFrame({COLS[c]: np.exp(res[c].seasonal).groupby(d.index.month).mean() for c in COLS}).round(3)
sf.index.name = "month"; sf.to_csv(RES / "seasonal_factor_by_month.csv"); print(sf)

# 季節成分の強さ（Wang et al. の指標：1 - Var(resid)/Var(seasonal+resid)）
strength = {COLS[c]: max(0, 1 - res[c].resid.var() / (res[c].seasonal + res[c].resid).var()) for c in COLS}
pd.Series(strength).round(3).to_csv(RES / "seasonal_strength.csv"); print(strength)

# 2) 年度ごとの3月の割合（12か月の均等なら8.3%）
rows = []
for fy, g in full.groupby("fy"):
    r = {"fy": fy}
    for c in COLS:
        r[c] = g.loc[g.month == 3, c].sum() / g[c].sum() * 100
    r["sep_total"] = g.loc[g.month == 9, "total"].sum() / g["total"].sum() * 100
    r["q4_total"] = g.loc[g.month.isin([1, 2, 3]), "total"].sum() / g["total"].sum() * 100
    rows.append(r)
mar = pd.DataFrame(rows).set_index("fy").round(2)
mar.to_csv(RES / "march_share_by_fy.csv"); print(mar)
trend = {COLS[c]: linregress(mar.index, mar[c])._asdict() for c in COLS}
tr = pd.DataFrame(trend).T[["slope", "pvalue"]].astype(float).round(4); tr.to_csv(RES / "march_share_trend.csv"); print(tr)
avg = mar[list(COLS)].mean().rename(index=COLS).round(1); print(avg)

# 3) 3月の受注額のうち、どの発注者が多いか（2011〜2025年度の合計）
m3 = full[full.month == 3][["private_mfg", "private_nonmfg", "public_national", "public_local", "other", "overseas"]].sum()
oth = full[full.month != 3][["private_mfg", "private_nonmfg", "public_national", "public_local", "other", "overseas"]].sum() / 11
comp = pd.DataFrame({"march_total": m3, "other_month_avg": oth})
comp["excess"] = comp.march_total / 15 - comp.other_month_avg / 15
comp["excess_share"] = comp.excess / comp.excess.sum() * 100
comp.round(1).to_csv(RES / "march_excess_by_client.csv"); print(comp.round(1))

# 図1 原系列とSTL（総計）
st = res["total"]
fig, axs = plt.subplots(3, 1, figsize=(10, 7.4), sharex=True, gridspec_kw={"height_ratios": [2, 1.2, 1]})
axs[0].plot(d.index, d.total / 1e6, color=GRAY, lw=1, label="受注高（月）")
axs[0].plot(d.index, np.exp(st.trend) / 1e6, color=BLUE, lw=2.2, label="トレンド")
m3i = d.index[d.month == 3]
axs[0].plot(m3i, d.loc[m3i, "total"] / 1e6, "o", color=ORANGE, ms=3.5, ls="none", label="3月")
axs[0].set_ylabel("兆円"); axs[0].legend(loc="upper left", frameon=False, fontsize=9)
axs[0].set_title("大手50社の受注高とSTL分解（総計、2011年1月〜2026年8月）", loc="left")
axs[1].plot(d.index, np.exp(st.seasonal), color=ORANGE, lw=1.2); axs[1].axhline(1, color=GRAY, lw=0.8)
axs[1].set_ylabel("季節の倍率")
axs[2].plot(d.index, np.exp(st.resid), color=INK, lw=0.9); axs[2].axhline(1, color=GRAY, lw=0.8)
axs[2].set_ylabel("残り（倍率）")
save(fig, "a225_stl.png")

# 図2 月別の季節の倍率（発注者別）
fig, ax = plt.subplots(figsize=(9.5, 4.8))
x = np.arange(1, 13); w = 0.2
pal = {"公共・国の機関": "#1f4e9c", "公共・地方の機関": BLUE, "民間・非製造業": ORANGE, "民間・製造業": "#e8a33d"}
for i, (k, c) in enumerate(pal.items()):
    ax.bar(x + (i - 1.5) * w, sf[k], w, color=c, label=k)
ax.plot(x, sf["総計"], color=INK, marker="o", lw=1.5, label="総計")
ax.axhline(1, color=GRAY, lw=0.8)
for k in ["総計"]:
    ax.text(3.15, sf.loc[3, k] + 0.08, f"総計 {sf.loc[3,k]:.2f}倍", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels([f"{m}月" for m in x])
ax.set_ylabel("季節の倍率（STL、1＝ふつうの月）")
ax.set_ylim(0, 3.4); ax.legend(ncol=5, frameon=False, fontsize=8.5, loc="upper right")
ax.set_title("どの月に受注が多いか（発注者別、2011〜2026年の平均）", loc="left")
save(fig, "a225_seasonal.png")

# 図3 3月の割合の推移
fig, ax = plt.subplots(figsize=(9.5, 4.8))
for c, col in [("total", INK), ("public_national", "#1f4e9c"), ("public_local", BLUE), ("private_nonmfg", ORANGE), ("private_mfg", "#e8a33d")]:
    ax.plot(mar.index, mar[c], marker="o", ms=3, lw=2.2 if c == "total" else 1.4, color=col)
    ax.text(2025.3, mar.loc[2025, c], f"{COLS[c]} {mar.loc[2025,c]:.0f}%", fontsize=8.5, color=col, va="center")
ax.axhline(100 / 12, color=GRAY, ls="--", lw=1); ax.text(2011, 100 / 12 + 0.6, "12か月で均等なら8.3%", fontsize=8.5, color=GRAY)
ax.set_xlim(2010.6, 2028.3); ax.set_ylabel("年度の受注高に占める3月の割合（%）"); ax.set_xlabel("年度")
ax.set_title("年度の受注のうち、3月に入った割合", loc="left")
save(fig, "a225_march_share.png")

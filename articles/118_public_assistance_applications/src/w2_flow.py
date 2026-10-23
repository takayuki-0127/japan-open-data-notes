"""W2：保護の申請件数・開始世帯数は月ごとにどう動くか（STL分解）。2020年度のコロナ期にどう動いたか。都道府県の保護率の差は縮まったか"""
from common import *
from statsmodels.tsa.seasonal import STL
import statsmodels.api as sm

f = load_flow().set_index("month").asfreq("MS")
KEYS = ["申請件数", "開始世帯数", "廃止世帯数"]

# --- 年度合計 ---
fy = f.groupby("fy")[KEYS].sum()
fy["開始÷申請%"] = fy["開始世帯数"] / fy["申請件数"] * 100
fy.round(1).to_csv(RES / "w2_fy.csv", encoding="utf-8-sig")

# --- STL（対数、周期12、ロバスト） ---
dec, seas = {}, {}
for k in ["申請件数", "開始世帯数"]:
    r = STL(np.log(f[k]), period=12, robust=True).fit()
    dec[k] = pd.DataFrame({"観測": f[k], "傾向": np.exp(r.trend), "季節%": (np.exp(r.seasonal) - 1) * 100,
                           "残差%": (np.exp(r.resid) - 1) * 100})
    s = dec[k]["季節%"]
    seas[k] = s.groupby(s.index.month).mean()
out = pd.concat({k: v for k, v in dec.items()}, axis=1)
out.round(2).to_csv(RES / "w2_stl.csv", encoding="utf-8-sig")
seas = pd.DataFrame(seas).round(2); seas.index.name = "月"
seas.to_csv(RES / "w2_seasonal.csv", encoding="utf-8-sig")
tr = dec["申請件数"]["傾向"]
tmin = tr.idxmin()

# --- 前年同月比（コロナ期） ---
yoy = (f[["申請件数", "開始世帯数"]].pct_change(12) * 100).round(1)
yoy.columns = [c + "_前年同月比%" for c in yoy.columns]
cv = pd.concat([f[["申請件数", "開始世帯数"]], yoy, dec["申請件数"]["残差%"].rename("申請件数_STL残差%").round(1)], axis=1)
cv.loc["2019-04":"2022-03"].to_csv(RES / "w2_covid.csv", encoding="utf-8-sig")

print(fy.round(1).to_string())
print("季節成分（%）", seas.to_string(), sep="\n")
print("申請件数の傾向：", {str(d.date()): round(v) for d, v in tr.iloc[::12].items()}, "最小", tmin.date(), round(tr.min()), "最終", round(tr.iloc[-1]))
print(cv.loc["2020-01":"2021-06"].to_string())

# --- 都道府県（指定都市・中核市を含む）の保護率 ---
pr = pref_rates()
p = pr.pivot(index="pref", columns="fy", values="rate").loc[PREFS]
p.round(2).to_csv(RES / "w2_pref_rate.csv", encoding="utf-8-sig")
disp = pd.DataFrame({"標準偏差": p.std(ddof=0), "平均": p.mean(), "変動係数": p.std(ddof=0) / p.mean(),
                     "最大": p.max(), "最小": p.min(), "最大÷最小": p.max() / p.min()})
u = load_units()
c = u[u.kind == "指定都市"].pivot(index="name", columns="fy", values="rate")
disp["指定都市_標準偏差"] = c.std(ddof=0)
disp["全国保護率"] = u[u.kind == "全国"].set_index("fy")["rate"]
disp.round(3).to_csv(RES / "w2_pref_dispersion.csv", encoding="utf-8-sig")
c.round(1).to_csv(RES / "w2_city_rate.csv", encoding="utf-8-sig")
d = p[2024] - p[2012]
beta = sm.OLS(d, sm.add_constant(p[2012])).fit(cov_type="HC1")
pd.DataFrame({"係数": beta.params, "標準誤差": beta.bse}).round(4).to_csv(RES / "w2_pref_beta.csv", encoding="utf-8-sig")
print(disp.round(3).to_string())
print("β（2012→2024の変化を2012の水準で回帰）", beta.params.round(3).to_dict(), beta.bse.round(3).to_dict(), "R2", round(beta.rsquared, 3))
print("上昇した都道府県", (d > 0).sum(), d.sort_values().round(1).iloc[[0, 1, 2, -3, -2, -1]].to_dict())
print("指定都市", c[[2012, 2024]].sort_values(2024).round(1).to_string())

# ===== 図1：申請・開始の推移と傾向、季節のパターン =====
fig, ax = plt.subplots(1, 2, figsize=(13, 4.8), gridspec_kw={"width_ratios": [1.5, 1]})
for k, col in [("申請件数", BLUE), ("開始世帯数", ORANGE)]:
    ax[0].plot(f.index, f[k] / 1e4, color=col, lw=.9, alpha=.45)
    ax[0].plot(f.index, dec[k]["傾向"] / 1e4, color=col, lw=2.2, label=f"{k}（細線：月の値、太線：STLの傾向）")
ax[0].axvspan(pd.Timestamp("2020-04-01"), pd.Timestamp("2021-03-31"), color=GRAY, alpha=.15, lw=0)
ax[0].text(pd.Timestamp("2020-05-01"), 1.43, "2020年度", fontsize=9, color="#555")
ax[0].annotate(f"傾向の底 {tmin:%Y年%-m月}\n{tr.min():,.0f}件", (tmin, tr.min() / 1e4), xytext=(pd.Timestamp("2014-06-01"), 1.5), textcoords="data",
               fontsize=9, arrowprops=dict(arrowstyle="-", color=INK, lw=.7))
ax[0].set_ylim(1.4, 2.8)
ax[0].set_title("保護の申請件数と保護開始世帯数（万、月次）", loc="left")
ax[0].legend(frameon=False, fontsize=9, loc="upper right")
mon = np.arange(1, 13); order = [4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2, 3]
x = np.arange(12)
ax[1].bar(x - .2, seas.loc[order, "申請件数"], width=.4, color=BLUE, label="申請件数")
ax[1].bar(x + .2, seas.loc[order, "開始世帯数"], width=.4, color=ORANGE, label="開始世帯数")
ax[1].axhline(0, color=INK, lw=.8)
ax[1].set_xticks(x); ax[1].set_xticklabels([f"{m}月" for m in order], fontsize=9)
ax[1].set_ylabel("季節成分（傾向からの％）")
ax[1].set_title("月ごとの季節のパターン（STL）", loc="left")
ax[1].legend(frameon=False, fontsize=9)
fig.text(0, -0.04, "注：2012年4月〜2025年3月。対数をとってSTL（周期12、ロバスト）で分解。季節成分は各月の平均。" + SOURCE, fontsize=7.5, color="#555")
fig.savefig(FIG / "w2_stl.png"); plt.close(fig)

# ===== 図2：コロナ期の前年同月比 =====
w = cv.loc["2019-04":"2022-03"]
fig, ax = plt.subplots(figsize=(11, 4.6))
xx = np.arange(len(w))
ax.bar(xx - .2, w["申請件数_前年同月比%"], width=.4, color=BLUE, label="申請件数")
ax.bar(xx + .2, w["開始世帯数_前年同月比%"], width=.4, color=ORANGE, label="開始世帯数")
ax.axhline(0, color=INK, lw=.8)
i0 = list(w.index).index(pd.Timestamp("2020-04-01"))
ax.annotate(f"2020年4月 申請 {w['申請件数_前年同月比%'].iloc[i0]:+.1f}%\n（{int(w['申請件数'].iloc[i0]):,}件）", (i0 - .2, w["申請件数_前年同月比%"].iloc[i0]),
            xytext=(25, -5), textcoords="offset points", fontsize=9, arrowprops=dict(arrowstyle="-", color=INK, lw=.7))
ax.axvspan(11.5, 23.5, color=GRAY, alpha=.12, lw=0)
ax.text(12, -15, "2020年度", fontsize=9, color="#555")
ax.set_xticks(xx[::3]); ax.set_xticklabels([f"{d:%Y年%-m月}" for d in w.index[::3]], fontsize=9)
ax.set_ylabel("前年同月比（％）")
ax.set_title("2020年4月に申請が急に増え、5〜8月は前の年を下回った", loc="left")
ax.legend(frameon=False, fontsize=9, loc="upper right")
fig.text(0, -0.05, "注：2019年4月〜2022年3月。月ごとの開庁日数の違いは調整していない。" + SOURCE, fontsize=7.5, color="#555")
fig.savefig(FIG / "w2_covid.png"); plt.close(fig)

# ===== 図3：都道府県の保護率 2012→2024年度 =====
fig, ax = plt.subplots(1, 2, figsize=(13, 5.2), gridspec_kw={"width_ratios": [1.25, 1]})
ax[0].scatter(p[2012], p[2024], s=22, color=BLUE, zorder=3)
lim = (0, 36)
ax[0].plot(lim, lim, color=GRAY, lw=.8, ls=":")
for n in ["大阪府", "北海道", "沖縄県", "高知県", "福岡県", "京都府", "東京都", "広島県", "宮城県", "富山県", "山口県"]:
    ax[0].annotate(n, (p.loc[n, 2012], p.loc[n, 2024]), xytext=(4, -3 if n not in ("長野県",) else 3), textcoords="offset points", fontsize=8.5)
ax[0].set_xlim(lim); ax[0].set_ylim(lim)
ax[0].set_xlabel("2012年度の保護率（人口千対）"); ax[0].set_ylabel("2024年度の保護率（人口千対）")
ax[0].set_title("都道府県の保護率：点線より下は下がった所", loc="left")
ax[1].plot(disp.index, disp["標準偏差"], color=BLUE, marker="o", ms=4, lw=1.8, label="都道府県の標準偏差（‰）")
ax2 = ax[1].twinx(); ax2.spines["right"].set_visible(True)
ax2.plot(disp.index, disp["変動係数"], color=ORANGE, marker="s", ms=4, lw=1.5, label="変動係数（右軸）")
ax2.set_ylim(0, .6)
ax[1].set_ylim(0, 8)
h1, l1 = ax[1].get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
ax[1].legend(h1 + h2, l1 + l2, frameon=False, fontsize=9, loc="lower left")
ax[1].set_title("都道府県のばらつき：少しずつ縮まっている", loc="left")
ax[1].set_xticks(disp.index[::2])
fig.text(0, -0.05, "注：都道府県の値は県内の指定都市・中核市を含めて計算（人口は各表の実人員÷保護率で近似）。" + SOURCE, fontsize=7.5, color="#555")
fig.savefig(FIG / "w2_pref.png"); plt.close(fig)
print("saved")

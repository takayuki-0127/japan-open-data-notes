"""J2：短い時間の大雨（1時間に50mm・80mm・100mm以上）は増えているか。どれくらいの速さで？
アメダスの年間回数（1,300地点あたり）に、ポアソン回帰と負の二項回帰で「10年あたりの倍率」を推定。気温との関係は、年ごとの差分どうしで見る"""
from common import *
import statsmodels.api as sm

r = pd.concat({k: read(f"amdhour{k}mm_p.csv").iloc[:, 0] for k in [50, 80, 100]}, axis=1).loc[:2025]
an = read("an_jpn.csv").iloc[:, 0]
r.to_csv(RES / "j2_counts.csv", encoding="utf-8-sig")
rows = []
for k in r.columns:
    y = r[k]; X = sm.add_constant(pd.Series((y.index.values - 2000) / 10, index=y.index, name="dec"))
    po = sm.GLM(y, X, family=sm.families.Poisson()).fit()
    disp = po.pearson_chi2 / po.df_resid
    qp = sm.GLM(y, X, family=sm.families.Poisson()).fit(scale="X2")
    nb = sm.NegativeBinomial(y, X).fit(disp=0)
    first, lastd = y.loc[1976:1985].mean(), y.loc[2016:2025].mean()
    rows.append(dict(threshold=f"{k}mm", rr10_poisson=np.exp(po.params["dec"]), dispersion=disp,
                     rr10_qp=np.exp(qp.params["dec"]), qp_lo=np.exp(qp.conf_int().loc["dec", 0]), qp_hi=np.exp(qp.conf_int().loc["dec", 1]),
                     rr10_nb=np.exp(nb.params.iloc[1]), nb_lo=np.exp(nb.conf_int().iloc[1, 0]), nb_hi=np.exp(nb.conf_int().iloc[1, 1]),
                     mean_1976_1985=first, mean_2016_2025=lastd, ratio_decades=lastd / first))
t = pd.DataFrame(rows).set_index("threshold"); t.round(4).to_csv(RES / "j2_trends.csv", encoding="utf-8-sig"); print(t.round(3).T)

# 気温との関係：対数回数の前年差を、気温偏差の前年差に回帰（共通のトレンドによる見かけの相関を避ける）
d = pd.DataFrame({"lr": np.log(r[50]), "t": an}).dropna()
lv = sm.OLS(d.lr, sm.add_constant(d.t)).fit(cov_type="HAC", cov_kwds={"maxlags": 3})
dd = d.diff().dropna(); fd = sm.OLS(dd.lr, sm.add_constant(dd.t)).fit(cov_type="HAC", cov_kwds={"maxlags": 3})
tt = sm.add_constant(np.column_stack([d.t, (d.index - 2000) / 10]))
both = sm.OLS(d.lr, tt).fit(cov_type="HAC", cov_kwds={"maxlags": 3})
temp = pd.DataFrame({"model": ["水準どうし", "前年差どうし", "トレンドも入れた水準"],
                     "pct_per_degC": [(np.exp(lv.params["t"]) - 1) * 100, (np.exp(fd.params["t"]) - 1) * 100, (np.exp(both.params.iloc[1]) - 1) * 100],
                     "lo": [(np.exp(lv.conf_int().loc["t", 0]) - 1) * 100, (np.exp(fd.conf_int().loc["t", 0]) - 1) * 100, (np.exp(both.conf_int().iloc[1, 0]) - 1) * 100],
                     "hi": [(np.exp(lv.conf_int().loc["t", 1]) - 1) * 100, (np.exp(fd.conf_int().loc["t", 1]) - 1) * 100, (np.exp(both.conf_int().iloc[1, 1]) - 1) * 100]})
temp.round(2).to_csv(RES / "j2_temperature.csv", index=False, encoding="utf-8-sig"); print(temp.round(1))
s = {f"{k}_{c}": t.loc[k, c] for k in t.index for c in ["rr10_qp", "qp_lo", "qp_hi", "dispersion", "mean_1976_1985", "mean_2016_2025", "ratio_decades"]}
s.update({"max_year_50": int(r[50].idxmax()), "max_50": r[50].max(), "n_years": len(r)})
pd.Series(s).to_csv(RES / "j2_summary.csv", header=["value"]); print(pd.Series(s).round(3))

note = "\n（アメダス地点で1時間降水量が基準以上になった年間の回数。年によって地点数が違うため、1,300地点あたりに換算した値）"
fig, axes = plt.subplots(1, 3, figsize=(13, 4))
for ax, k, c in zip(axes, [50, 80, 100], [BLUE, ORANGE, PURPLE]):
    y = r[k]; X = sm.add_constant(pd.Series((y.index.values - 2000) / 10, index=y.index, name="dec"))
    qp = sm.GLM(y, X, family=sm.families.Poisson()).fit(scale="X2")
    ax.bar(y.index, y, color=c, alpha=0.6, width=0.8)
    ax.plot(y.index, qp.fittedvalues, color=INK, lw=1.5)
    ax.set_title(f"{k}mm以上：10年で×{t.loc[f'{k}mm', 'rr10_qp']:.2f}（{t.loc[f'{k}mm', 'qp_lo']:.2f}〜{t.loc[f'{k}mm', 'qp_hi']:.2f}）", fontsize=10.5)
    ax.set_ylabel("回／年（1,300地点あたり）")
fig.suptitle("1時間に強い雨が降る回数は、強い雨ほど速く増えている", y=1.03)
fig.text(0.01, -0.08, SOURCE + note + "\n線は準ポアソン回帰（対数の直線トレンド）。括弧は95%区間", fontsize=7, color="#8a8984")
fig.savefig(FIG / "j2_trends.png"); plt.close(fig)

fig, ax = plt.subplots(figsize=(7, 4.6))
ax.scatter(dd.t, dd.lr * 100, color=BLUE, s=22)
xx = np.linspace(dd.t.min(), dd.t.max(), 10); ax.plot(xx, (fd.params["const"] + fd.params["t"] * xx) * 100, color=INK, lw=1)
ax.axhline(0, color=GRAY, lw=0.6); ax.axvline(0, color=GRAY, lw=0.6)
ax.set_xlabel("日本の年平均気温の前年差（℃）"); ax.set_ylabel("50mm以上の回数の前年比（対数×100）")
ax.set_title(f"気温が1℃上がった年、50mm以上の雨は{temp.pct_per_degC[1]:+.0f}%（95%区間 {temp.lo[1]:+.0f}〜{temp.hi[1]:+.0f}%）")
fig.text(0.01, -0.07, SOURCE + "\n（1977〜2025年。前年差どうしの回帰でトレンドの見かけの相関を除く。HAC標準誤差）", fontsize=7, color="#8a8984")
fig.savefig(FIG / "j2_temperature.png"); plt.close(fig)

"""H1：暑さ指数（WBGT）が上がると、熱中症の救急搬送はどれだけ増えるか。
6都市の日別データに、WBGT の非線形な効果（スプライン）と前日・前々日の効果を入れた準ポアソン回帰を当てはめ、WBGT25 に対する倍率の曲線を描く"""
from common import *
import statsmodels.api as sm
import statsmodels.formula.api as smf
from patsy import dmatrix, build_design_matrices

m = panel(); m.to_csv(RES / "h1_panel.csv", index=False, encoding="utf-8-sig")
KN = "bs(wbgt_max, knots=(22, 26, 29, 31), degree=2, lower_bound=5, upper_bound=37)"
f = f"n ~ {KN} + wbgt_l1 + wbgt_l2 + C(city) + C(year) + C(dow) + C(month)"
res = smf.glm(f, data=m, family=sm.families.Poisson(), offset=np.log(m["pop"])).fit(scale="X2")
print("dispersion", res.scale)

grid = pd.DataFrame({"wbgt_max": np.arange(14, 35.01, 0.25)})
spl_terms = [c for c in res.params.index if c.startswith("bs(")]
# スプライン部分だけの予測（基準 WBGT=25 との差）
base = dmatrix(KN, m, return_type="dataframe").design_info
Bg = np.asarray(build_design_matrices([base], grid)[0])[:, 1:]
B0 = np.asarray(build_design_matrices([base], pd.DataFrame({"wbgt_max": [25.0]}))[0])[:, 1:]
b = res.params[spl_terms].values; V = res.cov_params().loc[spl_terms, spl_terms].values
D = Bg - B0; eta = D @ b; se = np.sqrt(np.einsum("ij,jk,ik->i", D, V, D))
curve = pd.DataFrame({"wbgt": grid.wbgt_max, "rr": np.exp(eta), "lo": np.exp(eta - 1.96 * se), "hi": np.exp(eta + 1.96 * se)})
curve.round(4).to_csv(RES / "h1_curve.csv", index=False, encoding="utf-8-sig")
at = lambda w: curve.loc[(curve.wbgt - w).abs().idxmin()]
lag = {k: (np.exp(res.params[k]), np.exp(res.conf_int().loc[k, 0]), np.exp(res.conf_int().loc[k, 1])) for k in ["wbgt_l1", "wbgt_l2"]}

# 都市ごと（都市ごとに同じモデル）
cc = []
for c, g in m.groupby("city"):
    r = smf.glm(f.replace(" + C(city)", ""), data=g, family=sm.families.Poisson(), offset=np.log(g["pop"])).fit(scale="X2")
    bc = r.params[spl_terms].values; e = D @ bc
    cc.append(pd.DataFrame({"city": c, "wbgt": grid.wbgt_max, "rr": np.exp(e)}))
cc = pd.concat(cc); cc.round(4).to_csv(RES / "h1_curve_by_city.csv", index=False, encoding="utf-8-sig")
w_obs = m.groupby("city").wbgt_max.quantile([0.01, 0.99]).unstack()

# WBGT の区分ごとの平均搬送数（観測そのまま）
m["band"] = pd.cut(m.wbgt_max, [0, 21, 25, 28, 31, 40], right=False, labels=["21未満（ほぼ安全）", "21〜25（注意）", "25〜28（警戒）", "28〜31（厳重警戒）", "31以上（危険）"])
band = m.groupby("band", observed=True).agg(days=("rate", "size"), rate=("rate", "mean"), elderly_share=("elderly", "sum"), n=("n", "sum"))
band["elderly_share"] = band.elderly_share / band.n * 100; band.round(3).to_csv(RES / "h1_bands.csv", encoding="utf-8-sig"); print(band.round(2))

s = {"dispersion": res.scale, "n_obs": int(res.nobs), "rr28": at(28).rr, "rr28_lo": at(28).lo, "rr28_hi": at(28).hi, "rr31": at(31).rr, "rr31_lo": at(31).lo, "rr31_hi": at(31).hi,
     "rr33": at(33).rr, "rr33_lo": at(33).lo, "rr33_hi": at(33).hi, "rr20": at(20).rr,
     "lag1_rr": lag["wbgt_l1"][0], "lag1_lo": lag["wbgt_l1"][1], "lag1_hi": lag["wbgt_l1"][2], "lag2_rr": lag["wbgt_l2"][0], "lag2_lo": lag["wbgt_l2"][1], "lag2_hi": lag["wbgt_l2"][2],
     "rate_31plus_vs_21_25": band.loc["31以上（危険）", "rate"] / band.loc["21〜25（注意）", "rate"]}
pd.Series(s).to_csv(RES / "h1_summary.csv", header=["value"]); print(pd.Series(s).round(3))

note = "\n（2016〜2025年5〜9月、6都市（東京・大阪・名古屋・福岡・札幌・仙台）の日最高WBGTと、その都道府県の搬送人員。準ポアソン回帰：WBGTの2次スプライン＋前日・前々日のWBGT＋都市・年・曜日・月）"
fig, ax = plt.subplots(figsize=(9, 4.8))
ax.fill_between(curve.wbgt, curve.lo, curve.hi, color=LIGHT, alpha=0.7, lw=0)
ax.plot(curve.wbgt, curve.rr, color=ORANGE, lw=2.4)
for x0, lab in [(21, "注意"), (25, "警戒"), (28, "厳重警戒"), (31, "危険")]: ax.axvline(x0, color=GRAY, ls=":", lw=0.8); ax.text(x0 + 0.1, 0.9, lab, fontsize=8.5, color="#6b6a65")
ax.set_yscale("log"); ax.set_yticks([0.25, 0.5, 1, 2, 4, 8, 16]); ax.set_yticklabels(["0.25", "0.5", "1", "2", "4", "8", "16"])
ax.set_xlabel("その日の最高 WBGT（℃）"); ax.set_ylabel("搬送人員の倍率（WBGT25の日＝1）")
ax.set_title(f"WBGT31で約{s['rr31']:.1f}倍、33で約{s['rr33']:.1f}倍（WBGT25の日と比べて）")
fig.text(0.01, -0.08, SOURCE + note, fontsize=7, color="#8a8984"); fig.savefig(FIG / "h1_curve.png"); plt.close(fig)

fig, ax = plt.subplots(figsize=(9, 4.8))
cols = dict(zip(CITY, [BLUE, ORANGE, GREEN, PURPLE, GRAY, "#c4a000"]))
for c, g in cc.groupby("city"):
    lo, hi = w_obs.loc[c, 0.01], w_obs.loc[c, 0.99]; g = g[(g.wbgt >= lo) & (g.wbgt <= hi)]
    ax.plot(g.wbgt, g.rr, color=cols[c], lw=2, label=c)
ax.set_yscale("log"); ax.set_yticks([0.25, 0.5, 1, 2, 4, 8, 16]); ax.set_yticklabels(["0.25", "0.5", "1", "2", "4", "8", "16"])
ax.set_xlabel("その日の最高 WBGT（℃）"); ax.set_ylabel("WBGT25の日に対する倍率"); ax.legend(frameon=False, fontsize=9)
ax.set_title("都市ごとに当てはめても、曲線の形はよく似ている")
fig.text(0.01, -0.08, SOURCE + "\n（都市ごとに同じモデルを当てはめ。線はその都市で観測されたWBGTの1〜99%点の範囲だけ表示）", fontsize=7, color="#8a8984")
fig.savefig(FIG / "h1_city.png"); plt.close(fig)

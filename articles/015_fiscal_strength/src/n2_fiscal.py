"""N2：財政力指数が高い町は、住民の所得が高い町か（財政力指数 2022年度）"""
from common import *
from matplotlib.ticker import FixedLocator, NullLocator
SRC2 = "出典：e-Stat「統計でみる市区町村のすがた2026」「社会・人口統計体系 市区町村データ」を加工して作成"

d = load_extra(); d = d[d.D2201.notna()].copy()              # 東京23区は財政力指数がないので含まれない
d["fp"] = d.D2201
d["tax_pc"] = d.D320101 * 1e6 / d.A2301 / 1e4                 # 住民1人あたり地方税（万円）。D320101 は百万円
r = smf.ols("fp ~ z_log_inc + z_old + z_univ + z_log_density + z_mfg + z_primary + z_single + C(pref_code)", d).fit(cov_type="HC3")
d["resid"] = r.resid
s = {"n": len(d), "median_fp": d.fp.median(), "n_fp_ge1": int((d.fp >= 1).sum()), "corr_fp_loginc": np.corrcoef(d.fp, d.log_inc)[0, 1],
     "corr_fp_old": np.corrcoef(d.fp, d.old)[0, 1], "corr_fp_logdensity": np.corrcoef(d.fp, d.log_density)[0, 1], "r2_full": r.rsquared,
     "fp_ge1_income_below_median": int(((d.fp >= 1) & (d.inc < d.inc.median())).sum()), "median_tax_pc": d.tax_pc.median()}
pd.Series(s).round(3).to_csv(RES / "n2_summary.csv", header=["value"]); print(pd.Series(s).round(3))
cols = ["pref_name", "name", "A2301", "fp", "inc", "tax_pc", "resid"]
d.nlargest(20, "fp")[cols].round(2).to_csv(RES / "n2_top_fp.csv", index=False, encoding="utf-8-sig")
d.nlargest(20, "resid")[cols].round(2).to_csv(RES / "n2_top_resid.csv", index=False, encoding="utf-8-sig")
pd.DataFrame({"coef": r.params, "p": r.pvalues}).filter(like="z_", axis=0).round(3).to_csv(RES / "n2_model.csv", encoding="utf-8-sig")

# 図1：所得と財政力指数
fig, ax = plt.subplots(figsize=(8, 5))
ax.scatter(d.inc, d.fp, s=9, color=GRAY, alpha=0.55, lw=0)
lab = ["飛島村", "六ヶ所村", "泊村", "刈羽村", "軽井沢町", "武蔵野市", "浦安市", "芦屋市", "豊田市", "田尻町", "三島村"]
q = d[d["name"].isin(lab)]
ax.scatter(q.inc, q.fp, s=22, color=BLUE)
for _, x in q.iterrows():
    ax.annotate(x["name"], (x.inc, x.fp), xytext=(5, 2), textcoords="offset points", fontsize=8, color="#52514e")
ax.axhline(1, color=ORANGE, lw=1, ls="--"); ax.text(830, 1.03, "1.0（普通交付税を受けない目安）", fontsize=8, color="#52514e", ha="right")
ax.set_xscale("log"); ax.xaxis.set_major_locator(FixedLocator([250, 300, 400, 600, 900])); ax.xaxis.set_minor_locator(NullLocator()); ax.set_xticklabels(["250", "300", "400", "600", "900"])
ax.set_xlabel("納税者1人あたり所得（万円、対数目盛）"); ax.set_ylabel("財政力指数（2022年度）")
ax.set_title(f"所得が高い街ほど財政力も高い（相関 {s['corr_fp_loginc']:.2f}）。ただし上の方は別の顔ぶれ", loc="left")
fig.text(0.01, -0.03, SRC2 + "（東京23区は財政力指数がないため含まない）", fontsize=8, color="#8a8984"); fig.savefig(FIG / "n2_scatter.png"); plt.close(fig)

# 図2：条件をそろえても説明しきれない町（残差の上位）
t = d.nlargest(12, "resid").iloc[::-1]
fig, ax = plt.subplots(figsize=(8, 4.6)); y = np.arange(len(t))
ax.barh(y, t.resid, color=BLUE, height=0.65)
for yi, (_, x) in zip(y, t.iterrows()):
    ax.text(x.resid + 0.02, yi, f"指数 {x.fp:.2f}／所得 {x.inc:.0f}万円", va="center", fontsize=8)
ax.set_yticks(y, t["name"]); ax.set_xlim(0, 1.75); ax.set_xlabel("所得・年齢構成・産業などから予想される財政力指数との差")
ax.set_title("住民の所得などでは説明できないほど財政力が高い町", loc="left")
fig.text(0.01, -0.04, SRC2 + "／都道府県固定効果つき重回帰の残差", fontsize=8, color="#8a8984"); fig.savefig(FIG / "n2_resid.png"); plt.close(fig)

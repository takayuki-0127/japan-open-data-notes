"""S5：転入が増えた年に、その県の地価は上がったか（都道府県×年の二方向固定効果、2013〜2023年）"""
from common import *
import statsmodels.formula.api as smf
d, lab = read("SSDSE-B-2026")
d = d.rename(columns={d.columns[0]: "year", d.columns[1]: "code", d.columns[2]: "pref"})
p = d[d.code != "R00000"].sort_values(["pref", "year"]).copy()
p["net"] = (p.A5101 - p.A5102) / p.A1101 * 1000                 # 日本人の転入超過（人口1,000人あたり）
p["lp"] = np.log(p.C5401)                                        # 住宅地の標準価格（平均）
p["dlp"] = p.groupby("pref").lp.diff() * 100                     # 前年からの変化率（%、対数差）
p["net_l1"] = p.groupby("pref").net.shift(1)
q = p.dropna(subset=["dlp", "net_l1"])
rows = []
for name, f, x in [("そのまま", "dlp ~ net", "net"), ("二方向固定効果", "dlp ~ net + C(pref) + C(year)", "net"),
                   ("二方向固定効果・前年の転入超過", "dlp ~ net_l1 + C(pref) + C(year)", "net_l1"), ("逆向き：地価→転入超過", "net ~ dlp + C(pref) + C(year)", "dlp")]:
    r = smf.ols(f, q).fit(cov_type="cluster", cov_kwds={"groups": q["pref"]})
    rows.append({"model": name, "x": x, "coef": r.params[x], "lo": r.conf_int().loc[x, 0], "hi": r.conf_int().loc[x, 1], "p": r.pvalues[x], "r2": r.rsquared, "n": int(r.nobs)})
t = pd.DataFrame(rows); t.round(4).to_csv(RES / "s5_models.csv", index=False, encoding="utf-8-sig"); print(t.round(3))
yr = p.groupby("year")[["net", "dlp"]].mean(); yr.round(3).to_csv(RES / "s5_by_year.csv", encoding="utf-8-sig")
g = p[p.year == 2023]
s = {"n": len(q), "corr_2023": np.corrcoef(g.net, g.dlp)[0, 1], "n_pref_price_up_2023": int((g.dlp > 0).sum()), "n_pref_net_positive_2023": int((g.net > 0).sum())}
pd.Series(s).to_csv(RES / "s5_summary.csv", header=["value"]); print(pd.Series(s))
SRC = source("SSDSE-県別推移（SSDSE-B-2026）")

fig, ax = plt.subplots(figsize=(8, 5))
ax.scatter(g.net, g.dlp, color=BLUE, s=22)
for _, r in g.iterrows():
    if r.pref in ["東京都", "沖縄県", "福岡県", "北海道", "秋田県", "大阪府", "青森県", "埼玉県"]:
        ax.annotate(r.pref, (r.net, r.dlp), xytext=(4, 2), textcoords="offset points", fontsize=8, color="#52514e")
ax.axhline(0, color=GRAY, lw=0.8); ax.axvline(0, color=GRAY, lw=0.8)
ax.set_xlabel("日本人の転入超過（人口1,000人あたり、2023年）"); ax.set_ylabel("住宅地の地価の変化率（%、前年比）")
ax.set_title(f"2023年：転入が多い県ほど地価が上がった（相関 {s['corr_2023']:.2f}）", loc="left")
fig.text(0.01, -0.03, SRC, fontsize=7.5, color="#8a8984"); fig.savefig(FIG / "s5_scatter.png"); plt.close(fig)

fig, ax = plt.subplots(figsize=(8, 3.4)); y = np.arange(len(t))[::-1]
for yi, (_, r) in zip(y, t.iterrows()):
    c = BLUE if r.p < 0.05 else GRAY
    ax.hlines(yi, r.lo, r.hi, color=c, lw=2.5); ax.scatter(r.coef, yi, color=c, zorder=3); ax.text(r.hi + 0.02, yi, f"{r.coef:+.3f}", va="center", fontsize=9)
ax.axvline(0, color=INK, lw=0.8); ax.set_yticks(y, t.model); ax.set_xlabel("係数（上3つ：転入超過1人/1,000人あたりの地価の変化率%。下：地価1%あたりの転入超過）")
ax.set_title("同じ県の中でも、転入が多い年ほど地価が上がる", loc="left")
fig.text(0.01, -0.08, SRC + "（都道府県クラスター頑健標準誤差）", fontsize=7.5, color="#8a8984"); fig.savefig(FIG / "s5_coefs.png"); plt.close(fig)

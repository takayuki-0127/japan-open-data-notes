"""224 研究開発をする企業ほど、生産性は高いのか（企業活動基本調査、産業別 2020〜2024年度）"""
from common import *
import statsmodels.formula.api as smf

d = load()
d["lprod"] = np.log(d["prod"])
d["lrd"] = np.log1p(d["rd_int"])          # log(1+研究開発費売上高比率%)
d["lsize"] = np.log(d["size"])
d.to_csv(RES / "panel_industry_year.csv", index=False)

def fit(f, data, fe=False):
    m = smf.ols(f, data).fit(cov_type="cluster", cov_kwds={"groups": data["code"]})
    return m

rows = []
specs = {
    "A 交差項なし": "lprod ~ lrd + mfg + lsize + C(year)",
    "B 交差項（製造業×研究開発）": "lprod ~ lrd * mfg + lsize + C(year)",
    "C Bから学術・開発研究機関を除く": "lprod ~ lrd * mfg + lsize + C(year)",
    "D 研究開発をした企業の割合で": "lprod ~ I(rd_share/10) * mfg + lsize + C(year)",
    "E 産業の固定効果（同じ産業の中の変化）": "lprod ~ lrd + lrd:mfg + C(code) + C(year)",
}
models = {}
for k, f in specs.items():
    data = d[d.code != "710"] if k.startswith("C") else d
    m = fit(f, data); models[k] = m
    for v in m.params.index:
        if v.startswith("C(") or v == "Intercept": continue
        rows.append({"model": k, "term": v, "coef": m.params[v], "se": m.bse[v], "p": m.pvalues[v], "n": int(m.nobs), "r2": m.rsquared})
reg = pd.DataFrame(rows); reg.to_csv(RES / "regressions.csv", index=False)
print(reg.round(4).to_string())

# 研究開発費比率が1%→5%（log1p で 0.693→1.792）に上がったときの生産性の差（%）
mb = models["B 交差項（製造業×研究開発）"]
dl = np.log1p(5) - np.log1p(1)
eff_m = mb.params["lrd"] + mb.params["lrd:mfg"]; eff_n = mb.params["lrd"]
cov = mb.cov_params()
se_m = np.sqrt(cov.loc["lrd", "lrd"] + cov.loc["lrd:mfg", "lrd:mfg"] + 2 * cov.loc["lrd", "lrd:mfg"])
slope = pd.DataFrame({"group": ["製造業", "製造業以外"], "slope": [eff_m, eff_n], "se": [se_m, mb.bse["lrd"]],
                      "pct_1to5": [(np.exp(eff_m * dl) - 1) * 100, (np.exp(eff_n * dl) - 1) * 100]})
slope["lo95"] = (np.exp((slope.slope - 1.96 * slope.se) * dl) - 1) * 100
slope["hi95"] = (np.exp((slope.slope + 1.96 * slope.se) * dl) - 1) * 100
slope.to_csv(RES / "slope_by_group.csv", index=False); print(slope.round(3))

# 2024年度：研究開発をした企業の割合で4つに分けた生産性（製造業）
x = d[d.year == 2024].copy()
xm = x[x.mfg == 1].copy()
xm["q"] = pd.qcut(xm.rd_share, 4, labels=["下位25%", "25〜50%", "50〜75%", "上位25%"])
q = xm.groupby("q", observed=True).agg(n=("code", "size"), rd_share_med=("rd_share", "median"), rd_int_med=("rd_int", "median"),
                                       prod_med=("prod", "median"), prod_w=("value_added", "sum"), emp=("employees", "sum"))
q["prod_weighted"] = q.prod_w / q.emp * 100; q = q.drop(columns=["prod_w", "emp"])
q.round(1).to_csv(RES / "mfg_quartiles_2024.csv"); print(q.round(1))
corr = {g: x[x.mfg == v][["lprod", "lrd"]].corr().iloc[0, 1] for g, v in [("製造業", 1), ("製造業以外", 0)]}
pd.Series(corr).round(3).to_csv(RES / "corr_2024.csv"); print(corr)

# 図1 散布図（2024年度）
fig, axs = plt.subplots(1, 2, figsize=(11, 5), sharey=True)
for ax, (g, v, c) in zip(axs, [("製造業（59業種）", 1, BLUE), ("製造業以外（67業種）", 0, ORANGE)]):
    s = x[x.mfg == v]
    ax.scatter(s.rd_int + 0.01, s["prod"], s=np.sqrt(s.employees) / 4, color=c, alpha=0.65, edgecolor="white", lw=0.5)
    xs = np.linspace(0, s.rd_int.max(), 100)
    b = mb.params; base = b["Intercept"] + b["C(year)[T.2024]"] + b["lsize"] * s.lsize.mean()
    yv = np.exp(base + (b["mfg"] if v else 0) + (b["lrd"] + (b["lrd:mfg"] if v else 0)) * np.log1p(xs))
    ax.plot(xs + 0.01, yv, color=INK, lw=1.5)
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("研究開発費 ÷ 売上高（%、対数目盛。0は0.01に置いた）")
    ax.set_title(g, loc="left")
    lab = {"医薬品製造業", "光学機械器具・レンズ製造業", "タイヤ・チューブ製造業", "電気業", "学術・開発研究機関", "ソフトウェア業", "一般飲食店"}
    for _, r in s[s.name.isin(lab)].iterrows():
        ax.annotate(r["name"].replace("製造業", "").replace("機械器具・", ""), (r.rd_int + 0.01, r["prod"]), fontsize=7.5, xytext=(4, 3), textcoords="offset points")
    ax.text(0.97, 0.04, f"相関 {corr['製造業' if v else '製造業以外']:.2f}", transform=ax.transAxes, fontsize=9.5, ha="right", va="bottom")
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, p: f"{v:,.0f}")); ax.yaxis.set_minor_formatter(plt.NullFormatter())
    ax.set_yticks([300, 500, 1000, 2000, 4000])
axs[0].set_ylabel("付加価値額 ÷ 従業者数（万円/人、対数目盛）")
fig.suptitle("研究開発費の比率と労働生産性（2024年度、1点＝1業種、円の大きさ＝従業者数）", x=0.01, ha="left", fontsize=12)
save(fig, "a224_scatter.png")

# 図2 係数（交差項モデルの傾き＋他モデル）
fig, ax = plt.subplots(figsize=(10, 4.8))
items = []
for k in ["B 交差項（製造業×研究開発）", "C Bから学術・開発研究機関を除く", "E 産業の固定効果（同じ産業の中の変化）"]:
    m = models[k]; cv = m.cov_params()
    em = m.params["lrd"] + m.params["lrd:mfg"]; sm = np.sqrt(cv.loc["lrd", "lrd"] + cv.loc["lrd:mfg", "lrd:mfg"] + 2 * cv.loc["lrd", "lrd:mfg"])
    items += [(k[2:] + "：製造業", em, sm, BLUE), (k[2:] + "：製造業以外", m.params["lrd"], m.bse["lrd"], ORANGE)]
for i, (lab_, e, s_, c) in enumerate(items[::-1]):
    lo, hi = (np.exp((e - 1.96 * s_) * dl) - 1) * 100, (np.exp((e + 1.96 * s_) * dl) - 1) * 100
    ee = (np.exp(e * dl) - 1) * 100
    ax.plot([lo, hi], [i, i], color=c, lw=2); ax.plot(ee, i, "o", color=c)
    ax.text(hi + 2, i, f"{ee:+.0f}%（{lo:+.0f}〜{hi:+.0f}）", va="center", fontsize=8.5)
ax.set_yticks(range(len(items))); ax.set_yticklabels([t[0] for t in items[::-1]], fontsize=8.5)
ax.axvline(0, color=GRAY, lw=1)
ax.set_xlim(-20, 230)
ax.set_xlabel("研究開発費の比率が1%→5%のとき、労働生産性が何%違うか（95%信頼区間）")
ax.set_title("回帰で見た研究開発と生産性の関係（2020〜24年度、業種×年度）", loc="left")
save(fig, "a224_coef.png")

# 図3 製造業：研究開発をした企業の割合の4分位
fig, ax = plt.subplots(figsize=(8, 4.6))
ax.bar(range(4), q.prod_med, color=[LIGHT, LIGHT, BLUE, BLUE])
for i, (pw, pm, sh) in enumerate(zip(q.prod_weighted, q.prod_med, q.rd_share_med)):
    ax.text(i, pm + 20, f"{pm:,.0f}万円", ha="center", fontsize=10)
    ax.text(i, 60, f"研究開発をした\n企業 {sh:.0f}%", ha="center", fontsize=8.5, color=INK)
ax.set_xticks(range(4)); ax.set_xticklabels([f"{l}\n（{n}業種）" for l, n in zip(q.index, q.n)])
ax.set_ylabel("業種の生産性の中央値（万円/人）")
ax.set_title("製造業59業種を「研究開発をした企業の割合」で4つに分けた生産性（2024年度）", loc="left", fontsize=11.5)
save(fig, "a224_quartile.png")

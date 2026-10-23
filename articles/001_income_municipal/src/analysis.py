"""納税者1人あたりの所得（2024年度＝2023年の所得）は市区町村でどれだけ違い、何と関係しているか。
入力: data/processed/municipal_base.csv（estat-women-labor の build_dataset.py で作ったもの。e-Stat を加工）
出力: data/processed/*.csv, figures/*.png
"""
from pathlib import Path
import logging
import numpy as np, pandas as pd
import statsmodels.formula.api as smf
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.ticker import NullFormatter

logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f or "NotoSans-CJK" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": ["Noto Sans CJK JP", "IPAexGothic", "Yu Gothic", "Meiryo", "sans-serif"],
                     "axes.spines.top": False, "axes.spines.right": False, "font.size": 11, "axes.titlesize": 13,
                     "figure.dpi": 150, "savefig.bbox": "tight"})
ROOT = Path(__file__).resolve().parents[1]
OUT, FIG = ROOT / "data" / "processed", ROOT / "figures"
FIG.mkdir(exist_ok=True)
SOURCE = "出典：e-Stat「社会・人口統計体系 市区町村データ」「統計でみる市区町村のすがた2026」を加工して作成"
BLUE, ORANGE, GRAY, INK = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b"

d = pd.read_csv(OUT / "municipal_base.csv")
d = d[(d["A1101"] > 0) & (d["C120120"] > 0)].copy()
d["inc"] = d["C120110"] / d["C120120"] * 100              # 万円（課税対象所得 百万円 ÷ 納税義務者数）
d["log_inc"] = np.log(d["inc"])
d["ward23"] = (d["code"] // 1000 == 13) & (d["code"] % 1000 < 200) & (d["code"] % 1000 > 100)
d["taxpayer_rate"] = d["C120120"] / d["A2301"]           # 住民基本台帳人口（2024）あたり
d["univ_share"] = d["E9106"] / d["E9101"]
d["officer_share"] = d["F2402"] / d["F1102"]             # 就業者のうち役員
d["selfemp_share"] = (d["F2403"] + d["F2404"]) / d["F1102"]
d["old_share"] = d["A1303"] / d["A1101"]
d["commute_out"] = d["F2705"] / d["F1102"]
d["daynight"] = d["A6107"] / d["A1101"]
d["foreign_share"] = d["A1700"] / d["A1101"]
d["mfg_share"] = d["F2211"] / d["F1102"]
d["unemp_rate"] = d["F1107"] / d["F1101"]
X = ["univ_share", "officer_share", "selfemp_share", "old_share", "primary_share", "mfg_share",
     "unemp_rate", "log_density", "commute_out", "single_share", "foreign_share"]
LABEL = {"univ_share": "大学・大学院卒の割合", "officer_share": "就業者に占める会社役員の割合",
         "selfemp_share": "自営業（雇人あり・なし）の割合", "old_share": "65歳以上の割合",
         "primary_share": "第1次産業で働く人の割合", "mfg_share": "第2次産業で働く人の割合",
         "unemp_rate": "完全失業率", "log_density": "人口密度（可住地、対数）",
         "commute_out": "他の市区町村へ通勤する人の割合", "single_share": "単独世帯の割合",
         "foreign_share": "外国人の割合"}
m = d.dropna(subset=X + ["log_inc"]).copy()
for c in X:
    m["z_" + c] = (m[c] - m[c].mean()) / m[c].std()
Z = " + ".join("z_" + c for c in X)

# ---- 1. 分布 ----
desc = {"n": len(m), "mean": m.inc.mean(), "median": m.inc.median(), "p10": m.inc.quantile(.1),
        "p90": m.inc.quantile(.9), "max": m.inc.max(), "min": m.inc.min(),
        "p90_p10": m.inc.quantile(.9) / m.inc.quantile(.1), "max_min": m.inc.max() / m.inc.min(),
        "weighted_mean": (m.C120110.sum() / m.C120120.sum()) * 100}
pd.Series(desc).round(3).to_csv(OUT / "income_summary.csv", header=["value"])
cols = ["pref_name", "name", "inc", "taxpayer_rate", "univ_share", "officer_share", "A1101"]
pd.concat([m.nlargest(15, "inc")[cols].assign(group="上位"), m.nsmallest(15, "inc")[cols].assign(group="下位")]).round(3)\
    .to_csv(OUT / "income_top_bottom.csv", index=False, encoding="utf-8-sig")

# ---- 2. 回帰 ----
res = {}
res["univ_only"] = smf.ols("log_inc ~ z_univ_share", m).fit(cov_type="HC3")
res["full"] = smf.ols("log_inc ~ " + Z, m).fit(cov_type="HC3")
res["full_pref"] = smf.ols("log_inc ~ " + Z + " + C(pref_code)", m).fit(cov_type="HC3")
rob = {
    "都道府県クラスター標準誤差": smf.ols("log_inc ~ " + Z + " + C(pref_code)", m).fit(cov_type="cluster", cov_kwds={"groups": m["pref_code"]}),
    "納税者数で重みづけ": smf.wls("log_inc ~ " + Z + " + C(pref_code)", m, weights=m["C120120"]).fit(cov_type="HC3"),
    "東京23区を除く": smf.ols("log_inc ~ " + Z + " + C(pref_code)", m[~m.ward23]).fit(cov_type="HC3"),
    "人口5,000人以上": smf.ols("log_inc ~ " + Z + " + C(pref_code)", m[m.A1101 >= 5000]).fit(cov_type="HC3"),
    "所得の上位・下位1%を除く": smf.ols("log_inc ~ " + Z + " + C(pref_code)", m[m.inc.between(m.inc.quantile(.01), m.inc.quantile(.99))]).fit(cov_type="HC3"),
}
rows = []
for name, r in {"主モデル（都道府県固定効果）": res["full_pref"], "都道府県なし": res["full"], **rob}.items():
    for c in X:
        k = "z_" + c
        rows.append({"model": name, "var": LABEL[c], "coef": r.params[k], "lo": r.conf_int().loc[k, 0],
                     "hi": r.conf_int().loc[k, 1], "p": r.pvalues[k], "pct_per_sd": (np.exp(r.params[k]) - 1) * 100,
                     "n": int(r.nobs), "r2": r.rsquared})
tab = pd.DataFrame(rows).round(4)
tab.to_csv(OUT / "regression_income.csv", index=False, encoding="utf-8-sig")
r2 = {"大卒割合だけ": res["univ_only"].rsquared, "11変数": res["full"].rsquared, "11変数＋都道府県": res["full_pref"].rsquared}
pd.Series(r2).round(3).to_csv(OUT / "r2.csv", header=["r2"])
vif = {}
import statsmodels.stats.outliers_influence as oi
XX = m[["z_" + c for c in X]].assign(const=1).values
for i, c in enumerate(X):
    vif[LABEL[c]] = oi.variance_inflation_factor(XX, i)
pd.Series(vif).round(2).to_csv(OUT / "vif.csv", header=["vif"])
print(pd.Series(desc).round(2)); print({k: round(v, 3) for k, v in r2.items()})
print(tab[tab.model == "主モデル（都道府県固定効果）"][["var", "pct_per_sd", "lo", "hi", "p"]])
print(pd.Series(vif).round(2))

# ---- 図1：分布 ----
fig, ax = plt.subplots(figsize=(8, 4.2))
bins = np.logspace(np.log10(m.inc.min() * 0.95), np.log10(m.inc.max() * 1.05), 60)
ax.hist(m.inc, bins=bins, color=GRAY, edgecolor="white")
ax.hist(m.loc[m.ward23, "inc"], bins=bins, color=BLUE, edgecolor="white", label="東京23区")
ax.set_xscale("log"); ax.set_xticks([250, 300, 400, 500, 700, 1000, 1500]); ax.set_xticklabels(["250", "300", "400", "500", "700", "1,000", "1,500"]); ax.xaxis.set_minor_formatter(NullFormatter())
ax.axvline(m.inc.median(), color=INK, lw=1, ls="--"); ax.text(m.inc.median() * 1.01, ax.get_ylim()[1] * 0.92, f"中央値 {m.inc.median():.0f}万円", fontsize=9)
for (_, r), h in zip(m.nlargest(3, "inc").iterrows(), [22, 48, 22]):
    ax.annotate(f"{r['name']} {r.inc:,.0f}", (r.inc, 1), xytext=(r.inc * (1.04 if h == 48 else 1), h), ha="center", fontsize=8, color=BLUE, arrowprops=dict(arrowstyle="-", color=BLUE, lw=0.6))
ax.set_xlabel("納税者1人あたりの課税対象所得（万円、対数目盛）"); ax.set_ylabel("市区町村の数")
ax.set_title(f"全国{len(m):,}市区町村：多くは300万円台に集まり、ごく一部が大きく離れる", loc="left")
ax.legend(frameon=False, loc="upper right", bbox_to_anchor=(1, 0.85))
fig.text(0.01, -0.03, SOURCE + "（課税対象所得は2024年度＝2023年の所得）", fontsize=8, color="#8a8984")
fig.savefig(FIG / "fig1_distribution.png"); plt.close(fig)

# ---- 図2：大卒割合と所得 ----
fig, ax = plt.subplots(figsize=(8, 5))
o = m[~m.ward23]
ax.scatter(o.univ_share * 100, o.inc, s=np.clip(o.A1101 / 4000, 4, 120), color=GRAY, alpha=0.55, lw=0)
w = m[m.ward23]
ax.scatter(w.univ_share * 100, w.inc, s=np.clip(w.A1101 / 4000, 4, 120), color=BLUE, alpha=0.85, lw=0, label="東京23区")
for _, r in pd.concat([m.nlargest(5, "inc"), m.nlargest(3, "univ_share")]).drop_duplicates("code").iterrows():
    ax.annotate(r["name"], (r.univ_share * 100, r.inc), xytext=(4, 2), textcoords="offset points", fontsize=8, color="#52514e")
ax.set_yscale("log"); ax.set_yticks([250, 300, 400, 500, 700, 1000, 1500]); ax.set_yticklabels(["250", "300", "400", "500", "700", "1,000", "1,500"]); ax.yaxis.set_minor_formatter(NullFormatter())
cor = np.corrcoef(m.univ_share, m.log_inc)[0, 1]
ax.set_xlabel("大学・大学院卒の割合（%、2020年）"); ax.set_ylabel("納税者1人あたり所得（万円、対数目盛）")
ax.set_title(f"大卒の割合が高い街ほど所得が高い（相関 {cor:.2f}、円の大きさは人口）", loc="left")
ax.legend(frameon=False, loc="upper left")
fig.text(0.01, -0.03, SOURCE, fontsize=8, color="#8a8984")
fig.savefig(FIG / "fig2_univ_income.png"); plt.close(fig)

# ---- 図3：係数（主モデル）----
t = tab[tab.model == "主モデル（都道府県固定効果）"].copy()
t["lo_pct"], t["hi_pct"] = (np.exp(t.lo) - 1) * 100, (np.exp(t.hi) - 1) * 100
t = t.sort_values("pct_per_sd")
fig, ax = plt.subplots(figsize=(8, 5))
y = np.arange(len(t))
col = [BLUE if v > 0 else ORANGE for v in t.pct_per_sd]
ax.hlines(y, t.lo_pct, t.hi_pct, color=col, lw=2); ax.scatter(t.pct_per_sd, y, color=col, zorder=3)
ax.axvline(0, color=INK, lw=0.8); ax.set_yticks(y, t["var"]); ax.set_xlabel("その変数が1標準偏差高いと、所得は何%違うか（95%信頼区間）")
ax.set_title(f"ほかの条件と都道府県をそろえたときの関連（決定係数 {res['full_pref'].rsquared:.2f}）", loc="left")
fig.text(0.01, -0.03, SOURCE + "／重回帰・HC3 頑健標準誤差", fontsize=8, color="#8a8984")
fig.savefig(FIG / "fig3_coefficients.png"); plt.close(fig)

# ---- 図4：平均所得と納税者の割合 ----
fig, ax = plt.subplots(figsize=(8, 5))
ax.scatter(o.taxpayer_rate * 100, o.inc, s=10, color=GRAY, alpha=0.5, lw=0)
ax.scatter(w.taxpayer_rate * 100, w.inc, s=18, color=BLUE, alpha=0.85, lw=0, label="東京23区")
ax.set_yscale("log"); ax.set_yticks([250, 300, 400, 500, 700, 1000, 1500]); ax.set_yticklabels(["250", "300", "400", "500", "700", "1,000", "1,500"]); ax.yaxis.set_minor_formatter(NullFormatter())
ax.set_xlabel("住民に占める納税義務者の割合（%）"); ax.set_ylabel("納税者1人あたり所得（万円、対数目盛）")
ax.set_title(f"納税者の割合が高い街ほど、納税者の平均所得も高い（相関 {np.corrcoef(m.taxpayer_rate, m.log_inc)[0, 1]:.2f}）", loc="left"); ax.legend(frameon=False)
fig.text(0.01, -0.03, SOURCE + "（納税義務者は所得割、住民は2024年の住民基本台帳人口）", fontsize=8, color="#8a8984")
fig.savefig(FIG / "fig4_taxpayer_rate.png"); plt.close(fig)

m[["code", "pref_name", "name", "inc", "taxpayer_rate"] + X].round(4).to_csv(OUT / "municipal_income_dataset.csv", index=False, encoding="utf-8-sig")

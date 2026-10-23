"""2000〜2025年に食中毒の中身はどう変わったか：病因物質別の件数・患者数の推移、季節、トレンドの回帰"""
import numpy as np, pandas as pd, statsmodels.api as sm
import matplotlib.pyplot as plt
from common import *

x = load(False)
Y = range(2000, 2026)
n = x.groupby(["year", "group"]).size().unstack(fill_value=0).reindex(index=Y, columns=GROUPS, fill_value=0)
p = x.groupby(["year", "group"]).patients.sum().unstack(fill_value=0).reindex(index=Y, columns=GROUPS, fill_value=0)
n.to_csv(RES / "f1_count_by_group.csv", encoding="utf-8-sig"); p.to_csv(RES / "f1_patients_by_group.csv", encoding="utf-8-sig")
tot = x.groupby("year").agg(outbreaks=("patients", "size"), patients=("patients", "sum"), deaths=("deaths", "sum"))
tot.to_csv(RES / "f1_total.csv", encoding="utf-8-sig"); print(tot.T.to_string())
per = pd.DataFrame({"2000-04件": n.loc[2000:2004].mean(), "2021-25件": n.loc[2021:2025].mean(), "2000-04患者": p.loc[2000:2004].mean(), "2021-25患者": p.loc[2021:2025].mean()})
per["件数の比"] = per["2021-25件"] / per["2000-04件"]; per.to_csv(RES / "f1_period_compare.csv", encoding="utf-8-sig"); print(per.round(1))

# 年トレンド：準ポアソン回帰（件数 ~ 年 + 2020-22年ダミー）、群ごと。アニサキスは病因物質に加わった2013年以降だけ
tr = []
yrs = np.array(list(Y))
for g in GROUPS:
    keep = yrs >= (2013 if g == "アニサキス" else 2000)
    yv = n[g].values[keep]; t = yrs[keep] - 2000; covid = np.isin(yrs[keep], [2020, 2021, 2022]).astype(float)
    m = sm.GLM(yv, sm.add_constant(np.c_[t, covid]), family=sm.families.Poisson()).fit(scale="X2")
    ci = m.conf_int()[1]
    tr.append({"group": g, "期間": f"{yrs[keep][0]}-2025", "年あたり変化率%": (np.exp(m.params[1]) - 1) * 100, "lo": (np.exp(ci[0]) - 1) * 100, "hi": (np.exp(ci[1]) - 1) * 100,
               "コロナ期の比": np.exp(m.params[2]), "コロナ期_lo": np.exp(m.conf_int()[2][0]), "コロナ期_hi": np.exp(m.conf_int()[2][1]), "p": m.pvalues[1]})
TR = pd.DataFrame(tr); TR.to_csv(RES / "f1_trend_qp.csv", index=False, encoding="utf-8-sig"); print(TR.round(3))

# アニサキス：2012年まで「その他の寄生虫」扱い→2013年に病因物質へ追加。年別件数
ani = n["アニサキス"]; print(ani.to_dict())

# 季節：月×群の件数（2016-2025年）
s = x[x.year >= 2016].groupby(["group", "month"]).size().unstack(fill_value=0).reindex(index=GROUPS, columns=range(1, 13), fill_value=0)
sh = s.div(s.sum(axis=1), axis=0) * 100; sh.to_csv(RES / "f1_season_share.csv", encoding="utf-8-sig")

# 図1：件数の積み上げ（主要群）
fig, axes = plt.subplots(1, 2, figsize=(11, 4.3))
main = ["カンピロバクター", "ノロウイルス", "アニサキス", "サルモネラ", "腸炎ビブリオ", "植物性自然毒", "黄色ブドウ球菌", "動物性自然毒", "ウェルシュ菌", "腸管出血性大腸菌", "化学物質", "その他・不明"]
for ax, D, lab in [(axes[0], n, "事件数"), (axes[1], p / 1000, "患者数（千人）")]:
    ax.stackplot(list(Y), [D[g] for g in main], colors=[GCOL[g] for g in main], labels=main, alpha=.9)
    ax.set_title(lab, loc="left"); ax.set_xlim(2000, 2025)
axes[1].legend(frameon=False, fontsize=8, bbox_to_anchor=(1.01, 1), loc="upper left")
fig.suptitle("食中毒の事件数と患者数（病因物質別、2000〜2025年）", x=.02, y=1.03, ha="left", fontsize=12.5)
note(axes[0], SOURCE + "\n国外での発生は除く。小型球形ウイルス（2003年以前の名称）はノロウイルスに含めた", -0.12)
fig.savefig(FIG / "f1_stack.png"); plt.close(fig)

# 図2：主な5群の件数の推移
fig, ax = plt.subplots(figsize=(8.4, 4.2))
for g in ["カンピロバクター", "ノロウイルス", "アニサキス", "サルモネラ", "腸炎ビブリオ"]:
    ax.plot(list(Y), n[g], "o-", ms=3.5, lw=2, color=GCOL[g], label=g)
    ax.text(2025.3, n[g].iloc[-1] + {"サルモネラ": 14, "腸炎ビブリオ": -14}.get(g, 0), f"{g} {n[g].iloc[-1]}", color=GCOL[g], fontsize=9, va="center")
ax.axvspan(2019.5, 2022.5, color=LIGHT, alpha=.35, lw=0); ax.text(2021, ax.get_ylim()[1] * .95, "コロナ期", ha="center", fontsize=8.5, color=GRAY)
ax.set_xlim(2000, 2029); ax.set_ylabel("事件数（件）")
ax.set_title("主な病因物質の事件数", loc="left")
note(ax, SOURCE, -0.13); fig.savefig(FIG / "f1_lines.png"); plt.close(fig)

# 図3：季節（月別の割合のヒートマップ）
fig, ax = plt.subplots(figsize=(8.6, 4.6))
show = [g for g in GROUPS if g != "その他・不明"]
im = ax.imshow(sh.loc[show].values, cmap="Blues", aspect="auto", vmin=0, vmax=40)
for i, g in enumerate(show):
    for j in range(12):
        v = sh.loc[g, j + 1]; ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=7.5, color="white" if v > 22 else INK)
ax.set_xticks(range(12)); ax.set_xticklabels([f"{m}月" for m in range(1, 13)], fontsize=9); ax.set_yticks(range(len(show))); ax.set_yticklabels(show, fontsize=9.5)
ax.spines[:].set_visible(False); fig.colorbar(im, ax=ax, shrink=.8, label="その群の年間件数に占める割合（%）")
ax.set_title("何月に多いか（2016〜2025年の事件数、行ごとに合計100%）", loc="left", fontsize=12)
note(ax, SOURCE, -0.1); fig.savefig(FIG / "f1_season.png"); plt.close(fig)

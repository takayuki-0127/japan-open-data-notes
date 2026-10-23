"""賃貸用の空き家と使い道のない空き家（賃貸・売却用及び二次的住宅以外）：市区町村での相関、都市と地方、腐朽・破損、全国の推移"""
import numpy as np, pandas as pd, statsmodels.api as sm
import matplotlib.pyplot as plt
from common import *

x = load_muni()
for k in ("vacant", "rent", "other", "sale", "second"):
    x[f"{k}_r"] = x[k] / x.houses * 100
x["other_sh"] = x.other / x.vacant * 100
x["rent_sh"] = x.rent / x.vacant * 100
m = munis(x)

# 1) 2つの割合の相関（市区町村・都道府県、2018年と2023年）
cor = []
for y in (2018, 2023):
    s = m[m.year == y]; p = x[(x.year == y) & (x.level == "a") & (x.code != "00000")]
    cor.append({"year": y, "単位": "市区町村", "n": len(s), "pearson": s[["rent_r", "other_r"]].corr().iloc[0, 1],
                "spearman": s[["rent_r", "other_r"]].corr("spearman").iloc[0, 1],
                "corr_vacant_rent": s[["vacant_r", "rent_r"]].corr().iloc[0, 1], "corr_vacant_other": s[["vacant_r", "other_r"]].corr().iloc[0, 1]})
    cor.append({"year": y, "単位": "都道府県", "n": len(p), "pearson": p[["rent_r", "other_r"]].corr().iloc[0, 1],
                "spearman": p[["rent_r", "other_r"]].corr("spearman").iloc[0, 1],
                "corr_vacant_rent": p[["vacant_r", "rent_r"]].corr().iloc[0, 1], "corr_vacant_other": p[["vacant_r", "other_r"]].corr().iloc[0, 1]})
cor = pd.DataFrame(cor); cor.to_csv(RES / "w2_correlation.csv", index=False, encoding="utf-8-sig"); print(cor.round(3))
s23 = m[m.year == 2023].copy()
# 賃貸用と使い道のないものの、どちらが多いか
s23["main"] = np.where(s23.rent > s23.other, "賃貸用が多い", "使い道のないものが多い")
print(s23.groupby(["level", "main"]).size().unstack())

# 2) 都市と地方：区分（政令市の区・特別区・市・町村）と住宅数の規模別
s23["区分"] = s23.level.map({"0": "政令市の区・特別区", "2": "市", "3": "町村"})
s23["規模"] = pd.cut(s23.houses, [0, 10000, 30000, 100000, 1e9], labels=["1万戸未満", "1万〜3万戸", "3万〜10万戸", "10万戸以上"], right=False)
def agg(g):
    return pd.Series({"n": len(g), "空き家率_合計": g.vacant.sum() / g.houses.sum() * 100,
                      "賃貸用_率": g.rent.sum() / g.houses.sum() * 100, "使い道なし_率": g.other.sum() / g.houses.sum() * 100,
                      "賃貸用_率_中央値": g.rent_r.median(), "使い道なし_率_中央値": g.other_r.median(),
                      "空き家に占める使い道なし_%": g.other.sum() / g.vacant.sum() * 100,
                      "腐朽破損あり_使い道なし_%": g.rot_other.sum() / g.other.sum() * 100,
                      "腐朽破損あり_賃貸用_%": g.rot_rent.sum() / g.rent.sum() * 100,
                      "使い道なしのうち一戸建_%": g.det_other.sum() / g.other.sum() * 100})
grp = pd.concat({"区分": s23.groupby("区分").apply(agg).reindex(["政令市の区・特別区", "市", "町村"]), "規模": s23.groupby("規模").apply(agg)})
grp.to_csv(RES / "w2_urban_rural.csv", encoding="utf-8-sig"); print(grp.round(1).T.to_string())
# 住宅数（対数）との関係
for k in ("rent_r", "other_r"):
    r = sm.OLS(s23[k], sm.add_constant(np.log10(s23.houses))).fit(cov_type="HC1")
    print(k, "~ log10(住宅数)：傾き", round(r.params.iloc[1], 2), "SE", round(r.bse.iloc[1], 2), "R2", round(r.rsquared, 3))

# 3) 腐朽・破損あり（全国・2018/2023年、市区町村の分布）
nat = x[x.code == "00000"].set_index("year")
rot = pd.DataFrame({"空き家全体": nat.rot_vacant / nat.vacant * 100, "使い道のない空き家": nat.rot_other / nat.other * 100,
                    "賃貸用の空き家": nat.rot_rent / nat.rent * 100})
rot["使い道のない空き家_戸"] = nat.rot_other; rot["賃貸用の空き家_戸"] = nat.rot_rent
rot["使い道なし_一戸建の割合"] = nat.det_other / nat.other * 100
rot.to_csv(RES / "w2_rot_national.csv", encoding="utf-8-sig"); print(rot.round(1))
s23["rot_other_sh"] = s23.rot_other / s23.other * 100; s23["rot_rent_sh"] = s23.rot_rent / s23.rent * 100
print("市区町村の腐朽破損割合（中央値）使い道なし", s23.rot_other_sh.median().round(1), "賃貸用", s23.rot_rent_sh.median().round(1))

# 4) 全国の推移 1958〜2023年
n = load_national()
n["vacant_r"] = n.vacant / n.houses * 100
for k in ("other", "rent", "sale", "second"): n[f"{k}_r"] = n[k] / n.houses * 100
n["other_sh"] = n.other / n.vacant * 100
n.to_csv(RES / "w2_national_series.csv", index=False, encoding="utf-8-sig"); print(n.round(2).to_string())

# 図1：全国の推移
fig, ax = plt.subplots(figsize=(8.6, 4.4))
ax.plot(n.year, n.vacant_r, "-o", color=INK, ms=4, label="空き家全体")
k = n.dropna(subset=["rent_r"])
ax.plot(k.year, k.rent_r, "-o", color=BLUE, ms=4, label="賃貸用（1998年までは売却用を含む）")
ax.plot(k.year, k.other_r, "-o", color=ORANGE, ms=4, label="使い道のない空き家（2018年までは「その他の住宅」）")
k2 = n.dropna(subset=["second_r"])
ax.plot(k2.year, k2.second_r, "-", color=GRAY, lw=1.2, label="二次的住宅（別荘など）")
for _, r in n[n.year.isin([1958, 1983, 2023])].iterrows():
    ax.annotate(f"{r.vacant_r:.1f}%", (r.year, r.vacant_r), textcoords="offset points", xytext=(0, 7), ha="center", fontsize=8.5)
for _, r in k[k.year.isin([1983, 2023])].iterrows():
    ax.annotate(f"{r.other_r:.1f}%", (r.year, r.other_r), textcoords="offset points", xytext=(0, -14), ha="center", fontsize=8.5, color=ORANGE)
    ax.annotate(f"{r.rent_r:.1f}%", (r.year, r.rent_r), textcoords="offset points", xytext=(0, 7), ha="center", fontsize=8.5, color=BLUE)
ax.set_ylabel("総住宅数に対する割合（%）"); ax.set_ylim(0, 16)
ax.set_title("全国の空き家率と種類別の割合（1958〜2023年）", loc="left"); ax.legend(frameon=False, fontsize=8.5, loc="upper left")
note(ax, SOURCE + "。1968年までは沖縄県を含まない", y=-0.12)
fig.savefig(FIG / "w2_national.png"); plt.close(fig)

# 図2：市区町村の散布図（2023年）
fig, ax = plt.subplots(figsize=(7.6, 6.0))
cc = {"政令市の区・特別区": PURPLE, "市": BLUE, "町村": ORANGE}
for g_, c in cc.items():
    s = s23[s23["区分"] == g_]
    ax.scatter(s.rent_r, s.other_r, s=12, color=c, alpha=.5, lw=0, label=f"{g_}（{len(s)}）")
c23 = cor[(cor.year == 2023) & (cor["単位"] == "市区町村")].iloc[0]
ax.plot([0, 20], [0, 20], color=GRAY, lw=.8, ls=":")
ax.set_xlim(0, 22); ax.set_ylim(0, 35)
ax.set_xlabel("賃貸用の空き家÷総住宅数（%）"); ax.set_ylabel("使い道のない空き家÷総住宅数（%）")
ax.set_title("賃貸用と使い道のない空き家は別の所に多い（2023年）", loc="left")
ax.text(.5, 33, f"相関 {c23.pearson:.2f}（順位相関 {c23.spearman:.2f}）、{int(c23.n):,}市区町村", fontsize=9)
ax.legend(frameon=False, fontsize=9, loc="upper right"); note(ax, SOURCE + "。軽井沢町など二次的住宅の多い町は空き家率が高くても両方低く出る", y=-0.11)
fig.savefig(FIG / "w2_scatter.png"); plt.close(fig)

# 図3：規模別の構成と腐朽・破損
fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.2), gridspec_kw={"width_ratios": [1.25, 1]})
g = grp.loc["規模"]
yy = np.arange(len(g)); ax = axes[0]
ax.barh(yy + .2, g["賃貸用_率"], .4, color=BLUE, label="賃貸用")
ax.barh(yy - .2, g["使い道なし_率"], .4, color=ORANGE, label="使い道のない空き家")
for i, (a_, b_) in enumerate(zip(g["賃貸用_率"], g["使い道なし_率"])):
    ax.text(a_ + .2, i + .2, f"{a_:.1f}", va="center", fontsize=8.5); ax.text(b_ + .2, i - .2, f"{b_:.1f}", va="center", fontsize=8.5)
ax.set_yticks(yy); ax.set_yticklabels([f"{i}（{int(v)}）" for i, v in zip(g.index, g.n)], fontsize=9)
ax.set_xlabel("総住宅数に対する割合（%、合計で計算）"); ax.set_title("住宅数の規模別（2023年）", loc="left"); ax.legend(frameon=False, fontsize=9)
ax = axes[1]
rr = rot.loc[[2018, 2023], ["使い道のない空き家", "賃貸用の空き家", "空き家全体"]]
xx = np.arange(3)
ax.bar(xx - .18, rr.loc[2018], .36, color=GRAY, label="2018年"); ax.bar(xx + .18, rr.loc[2023], .36, color=BLUE, label="2023年")
for i, c_ in enumerate(rr.columns):
    ax.text(i - .18, rr.loc[2018, c_] + .5, f"{rr.loc[2018, c_]:.1f}", ha="center", fontsize=8.5)
    ax.text(i + .18, rr.loc[2023, c_] + .5, f"{rr.loc[2023, c_]:.1f}", ha="center", fontsize=8.5)
ax.set_xticks(xx); ax.set_xticklabels(["使い道のない", "賃貸用", "空き家全体"], fontsize=9)
ax.set_ylabel("腐朽・破損ありの割合（%）"); ax.set_title("腐朽・破損のある空き家（全国）", loc="left"); ax.legend(frameon=False, fontsize=9)
note(axes[0], SOURCE, y=-0.17)
fig.tight_layout(); fig.savefig(FIG / "w2_size_rot.png"); plt.close(fig)
print("figures done")

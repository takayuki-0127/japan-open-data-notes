"""W2：都道府県の平均年収の差は「職種の構成」と「同じ職種の中での賃金」のどちらから来ているか（シフト・シェア分解）。男女差も同じ方法で分ける"""
from common import *
o = load_occ().dropna(subset=["annual", "workers"])
o.to_csv(RES / "w2_occ_long.csv", index=False, encoding="utf-8-sig")


def decompose(sp, wp, sn, wn):
    """平均の差 = 構成効果 Σ(sp-sn)wn + 賃金効果 Σ sn(wp-wn) + 交差項 Σ(sp-sn)(wp-wn)"""
    idx = sp.index.intersection(sn.index)
    sp, wp, sn, wn = sp[idx] / sp[idx].sum(), wp[idx], sn[idx] / sn[idx].sum(), wn[idx]
    comp = ((sp - sn) * wn).sum(); rate = (sn * (wp - wn)).sum(); inter = ((sp - sn) * (wp - wn)).sum()
    return (sp * wp).sum() - (sn * wn).sum(), comp, rate, inter


def stacked(ax, y, parts, cols, labels):
    """正の値は右へ、負の値は左へ積み上げる（合計＝点の位置）"""
    pos = np.zeros(len(y)); neg = np.zeros(len(y))
    for v, c, l in zip(parts, cols, labels):
        v = np.asarray(v, float); left = np.where(v >= 0, pos, neg)
        ax.barh(y, v, left=left, color=c, height=0.7, label=l)
        pos = pos + np.where(v >= 0, v, 0); neg = neg + np.where(v < 0, v, 0)


# 1) 都道府県 vs 全国（男女計）
t = o[o.sex == "計"].set_index(["pref", "occ"])
n = t.loc["全国"]
rows = []
for p in PREFS:
    x = t.loc[p]
    gap, comp, rate, inter = decompose(x.workers, x.annual, n.workers, n.annual)
    rows.append(dict(pref=p, mean=(x.workers * x.annual).sum() / x.workers.sum(), gap=gap, comp=comp, rate=rate, inter=inter))
d = pd.DataFrame(rows).set_index("pref")
d.round(1).to_csv(RES / "w2_pref_vs_nat.csv", encoding="utf-8-sig")
share_rate = (d.rate.abs() / (d.comp.abs() + d.rate.abs() + d.inter.abs())).median() * 100
var_rate = np.var(d.rate) / np.var(d.gap) * 100; var_comp = np.var(d.comp) / np.var(d.gap) * 100

# 職種構成の差（東京と全国）
mix = t.workers.unstack("occ"); mix = mix.div(mix.sum(axis=1), axis=0) * 100
mix.round(2).to_csv(RES / "w2_occ_mix.csv", encoding="utf-8-sig")

# 2) 男女差（都道府県ごと）：女性の構成を男性に合わせたら差はどれだけ縮むか
g = []
for p in ["全国"] + PREFS:
    m = o[(o.pref == p) & (o.sex == "男")].set_index("occ"); f = o[(o.pref == p) & (o.sex == "女")].set_index("occ")
    gap, comp, rate, inter = decompose(f.workers, f.annual, m.workers, m.annual)  # 女性−男性
    g.append(dict(pref=p, men=(m.workers * m.annual).sum() / m.workers.sum(), gap=gap, comp=comp, rate=rate, inter=inter))
g = pd.DataFrame(g).set_index("pref"); g["gap_pct"] = g.gap / g.men * 100; g["rate_pct"] = g.rate / g.men * 100; g["comp_pct"] = g.comp / g.men * 100
g.round(2).to_csv(RES / "w2_gender.csv", encoding="utf-8-sig")
# 職種別の男女比（全国）
occ_ratio = (o[(o.pref == "全国") & (o.sex == "女")].set_index("occ").annual / o[(o.pref == "全国") & (o.sex == "男")].set_index("occ").annual * 100)
fshare = (o[(o.pref == "全国") & (o.sex == "女")].set_index("occ").workers / o[(o.pref == "全国") & (o.sex == "計")].set_index("occ").workers * 100)
pd.DataFrame({"women_per_men_pct": occ_ratio, "women_share_pct": fshare}).round(1).to_csv(RES / "w2_occ_gender.csv", encoding="utf-8-sig")

s = {"nat_mean": (n.workers * n.annual).sum() / n.workers.sum(), "tokyo_gap": d.loc["東京", "gap"], "tokyo_comp": d.loc["東京", "comp"], "tokyo_rate": d.loc["東京", "rate"],
     "min_pref": d.gap.idxmin(), "min_gap": d.gap.min(), "min_comp": d.loc[d.gap.idxmin(), "comp"], "min_rate": d.loc[d.gap.idxmin(), "rate"],
     "median_share_rate_pct": share_rate, "var_share_rate_pct": var_rate, "var_share_comp_pct": var_comp,
     "n_comp_pos": int((d.comp > 0).sum()), "tokyo_mgr_share": mix.loc["東京", "管理的職業従事者"], "nat_mgr_share": mix.loc["全国", "管理的職業従事者"],
     "tokyo_pro_share": mix.loc["東京", "専門的・技術的職業従事者"], "nat_pro_share": mix.loc["全国", "専門的・技術的職業従事者"],
     "nat_gender_gap_pct": g.loc["全国", "gap_pct"], "nat_gender_comp_pct": g.loc["全国", "comp_pct"], "nat_gender_rate_pct": g.loc["全国", "rate_pct"],
     "median_pref_gender_gap_pct": g.drop("全国").gap_pct.median(), "median_pref_gender_rate_share": (g.drop("全国").rate / g.drop("全国").gap).median() * 100,
     "max_gender_gap_pref": g.drop("全国").gap_pct.idxmin(), "max_gender_gap": g.drop("全国").gap_pct.min(),
     "min_gender_gap_pref": g.drop("全国").gap_pct.idxmax(), "min_gender_gap": g.drop("全国").gap_pct.max()}
pd.Series(s).to_csv(RES / "w2_summary.csv", header=["value"]); print(pd.Series(s)); print(occ_ratio.round(1)); print(fshare.round(1))
print(d.sort_values("gap").round(0).to_string())

note = "\n（一般労働者・産業計・企業規模10人以上。年収＝きまって支給する現金給与額×12＋年間賞与その他特別給与額。職種は大分類11区分、「不詳」を除く）"
# 図1 都道府県の分解
o2 = d.sort_values("gap")
fig, ax = plt.subplots(figsize=(8, 10.5))
y = np.arange(47)
stacked(ax, y, [o2.rate / 10, o2.comp / 10, o2.inter / 10], [BLUE, ORANGE, LIGHT], ["同じ職種の中での賃金の差", "職種の構成の差", "交差項"])
ax.scatter(o2.gap / 10, y, color=INK, s=14, zorder=3, label="全国との差（合計）")
ax.set_yticks(y); ax.set_yticklabels(o2.index, fontsize=8); ax.axvline(0, color=GRAY, lw=0.8)
ax.set_xlabel("全国平均との年収の差（万円）"); ax.legend(frameon=False, loc="lower right", fontsize=9)
ax.set_title("全国との差の大半は「同じ職種でも賃金が違う」こと")
fig.text(0.01, -0.03, SOURCE + note, fontsize=7, color="#8a8984"); fig.savefig(FIG / "w2_pref.png"); plt.close(fig)

# 図2 職種構成（東京・全国・最も低い県）
lo = d.gap.idxmin(); cmp = mix.loc[["東京", "全国", lo]].T
fig, ax = plt.subplots(figsize=(9, 4.8)); yy = np.arange(len(OCCS)); hgt = 0.27
for i, (p, col) in enumerate([("東京", INK), ("全国", BLUE), (lo, ORANGE)]):
    ax.barh(yy + (i - 1) * hgt, cmp.loc[OCCS, p], height=hgt, color=col, label=p)
ax.set_yticks(yy); ax.set_yticklabels(OCCS, fontsize=9); ax.invert_yaxis(); ax.set_xlabel("一般労働者に占める割合（%）"); ax.legend(frameon=False)
ax.set_title("東京は専門職・事務が多く、生産工程が少ない")
fig.text(0.01, -0.04, SOURCE + note, fontsize=7, color="#8a8984"); fig.savefig(FIG / "w2_mix.png"); plt.close(fig)

# 図3 男女差の分解
g2 = g.drop("全国").sort_values("gap_pct")
fig, ax = plt.subplots(figsize=(8, 10.5))
stacked(ax, y, [g2.rate_pct, g2.comp_pct, g2.inter / g2.men * 100], [BLUE, ORANGE, LIGHT], ["同じ職種の中での男女差", "男女で職種の構成が違うこと", "交差項"])
ax.scatter(g2.gap_pct, y, color=INK, s=14, zorder=3, label="男女差（合計）")
ax.set_yticks(y); ax.set_yticklabels(g2.index, fontsize=8); ax.axvline(0, color=GRAY, lw=0.8)
ax.set_xlabel("女性の平均年収 − 男性の平均年収（男性の平均に対する%）"); ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.06), ncol=2, fontsize=9)
ax.set_title("男女差も、大半は同じ職種の中で生じている")
fig.text(0.01, -0.07, SOURCE + note + "\n基準は男性（女性の職種構成を男性に合わせた場合との比較）", fontsize=7, color="#8a8984"); fig.savefig(FIG / "w2_gender.png"); plt.close(fig)

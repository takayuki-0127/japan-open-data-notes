"""T2：2016〜2026年の外国人の増え方は、区市町村でどれだけ違い、その違いは「どの国籍が住んでいたか」で説明できるか。
シフト・シェア分解（都全体の伸び・国籍構成・地域独自の伸び）と、国籍の多様性（シャノン・エントロピー）の推移"""
from common import *

x = load(); x = x[x.nat != "総数"]
A, B = 2016, 2026
m0 = x[x.year == A].pivot_table(index="area", columns="nat", values="n").fillna(0)
m1 = x[x.year == B].pivot_table(index="area", columns="nat", values="n").fillna(0).reindex(index=m0.index, columns=m0.columns).fillna(0)
g_all = m1.values.sum() / m0.values.sum() - 1
g_k = m1.sum() / m0.sum() - 1
n0 = m0.sum(axis=1); n1 = m1.sum(axis=1)
d = pd.DataFrame({"n2016": n0, "n2026": n1})
d["change"] = n1 - n0
d["tokyo_effect"] = n0 * g_all                                   # 都全体と同じ率で伸びた場合
d["mix_effect"] = (m0 * g_k).sum(axis=1) - n0 * g_all            # 伸びの大きい国籍が多く住んでいた分
d["local_effect"] = d.change - d.tokyo_effect - d.mix_effect     # その区市町村独自の伸び
d["growth_pct"] = d.change / n0 * 100
for c in ["tokyo_effect", "mix_effect", "local_effect"]: d[c + "_pct"] = d[c] / n0 * 100
d = d.sort_values("n2026", ascending=False); d.round(1).to_csv(RES / "t2_shiftshare.csv", encoding="utf-8-sig")
print(d.round(1).head(25).to_string())
gk = g_k.sort_values(ascending=False) * 100; gk.round(1).to_csv(RES / "t2_growth_by_nat.csv", header=["growth_pct"], encoding="utf-8-sig"); print(gk.round(1))
big = d[d.n2016 >= 1000]
var = lambda s: np.var(s)
vs = {"var_growth": var(big.growth_pct), "share_mix": np.cov(big.mix_effect_pct, big.growth_pct)[0, 1] / var(big.growth_pct) * 100,
      "share_local": np.cov(big.local_effect_pct, big.growth_pct)[0, 1] / var(big.growth_pct) * 100}

# 多様性：国籍（17区分、「その他」も1区分）のシャノン・エントロピーを最大値で割った値（0〜1）
ent = []
for y in sorted(x.year.unique()):
    m = x[x.year == y].pivot_table(index="area", columns="nat", values="n").fillna(0)
    p = m.div(m.sum(axis=1), axis=0); h = -(p * np.log(p.where(p > 0))).sum(axis=1) / np.log(m.shape[1])
    pt = m.sum() / m.values.sum(); ht = -(pt * np.log(pt[pt > 0])).sum() / np.log(m.shape[1])
    ent.append(dict(year=y, tokyo=ht, muni_median=h[m.sum(axis=1) >= 500].median(), muni_p10=h[m.sum(axis=1) >= 500].quantile(0.1), muni_p90=h[m.sum(axis=1) >= 500].quantile(0.9)))
ent = pd.DataFrame(ent).set_index("year"); ent.round(4).to_csv(RES / "t2_entropy.csv", encoding="utf-8-sig"); print(ent.round(3).iloc[::5])

s = {"g_all_pct": g_all * 100, "n_munis": len(d), "n_big": len(big), **vs,
     "top_growth": big.growth_pct.idxmax(), "top_growth_pct": big.growth_pct.max(), "low_growth": big.growth_pct.idxmin(), "low_growth_pct": big.growth_pct.min(),
     "top_local": big.local_effect_pct.idxmax(), "top_local_pct": big.local_effect_pct.max(), "low_local": big.local_effect_pct.idxmin(), "low_local_pct": big.local_effect_pct.min(),
     "ent_tokyo_1979": ent.tokyo.iloc[0], "ent_tokyo_2026": ent.tokyo.iloc[-1], "ent_med_1979": ent.muni_median.iloc[0], "ent_med_2026": ent.muni_median.iloc[-1]}
pd.Series(s).to_csv(RES / "t2_summary.csv", header=["value"]); print(pd.Series(s))

note = "\n（2016年1月1日→2026年1月1日。国籍は時系列表の17区分（中国・台湾、韓国・朝鮮は合算、ネパールなどは「その他」）。2016年に1,000人以上の区市町村）"
o = big.sort_values("growth_pct")
fig, ax = plt.subplots(figsize=(9, 11))
y = np.arange(len(o)); pos = np.zeros(len(o)); neg = np.zeros(len(o))
for c, col, lab in [("tokyo_effect_pct", GRAY, "都全体の伸び"), ("mix_effect_pct", ORANGE, "国籍構成の効果"), ("local_effect_pct", BLUE, "地域独自の伸び")]:
    v = o[c].values; left = np.where(v >= 0, pos, neg); ax.barh(y, v, left=left, color=col, height=0.7, label=lab)
    pos += np.where(v >= 0, v, 0); neg += np.where(v < 0, v, 0)
ax.scatter(o.growth_pct, y, color=INK, s=12, zorder=3, label="実際の増加率")
ax.set_yticks(y); ax.set_yticklabels(o.index, fontsize=8); ax.axvline(0, color=GRAY, lw=0.8)
ax.set_xlabel("2016〜2026年の外国人の増加率（%）"); ax.legend(frameon=False, loc="lower right", fontsize=9)
ax.set_title(f"都全体は+{g_all*100:.0f}%。区市ごとの差の多くは「地域独自の伸び」")
fig.text(0.01, -0.03, SOURCE + note, fontsize=7, color="#8a8984"); fig.savefig(FIG / "t2_shiftshare.png"); plt.close(fig)

fig, ax = plt.subplots(figsize=(8, 4.6))
ax.barh(range(len(gk)), gk.values, color=[ORANGE if v > g_all * 100 else BLUE for v in gk.values])
ax.axvline(g_all * 100, color=INK, ls="--", lw=1); ax.text(g_all * 100, len(gk) - 0.5, f" 全体 +{g_all*100:.0f}%", fontsize=8.5, va="bottom")
ax.set_yticks(range(len(gk))); ax.set_yticklabels(gk.index, fontsize=9); ax.invert_yaxis(); ax.set_xlabel("2016〜2026年の増加率（%）")
ax.set_title("国籍・地域ごとの増加率（東京都全体）")
fig.text(0.01, -0.06, SOURCE + "\n（2016年1月1日→2026年1月1日）", fontsize=7, color="#8a8984"); fig.savefig(FIG / "t2_growth_by_nat.png"); plt.close(fig)

fig, ax = plt.subplots(figsize=(10, 4.4))
ax.plot(ent.index, ent.tokyo, color=INK, lw=2, label="東京都全体")
ax.plot(ent.index, ent.muni_median, color=BLUE, lw=2, label="区市町村の中央値")
ax.fill_between(ent.index, ent.muni_p10, ent.muni_p90, color=LIGHT, alpha=0.6, lw=0, label="区市町村の10〜90%点")
ax.set_ylim(0, 1); ax.set_ylabel("国籍の多様性（0〜1）"); ax.legend(frameon=False, fontsize=9, loc="lower right")
ax.set_title("国籍の多様性は1999年まで上がり、2015年ごろから再び上昇")
fig.text(0.01, -0.06, SOURCE + "\n（シャノン・エントロピーを最大値で割った値。17区分。外国人500人以上の区市町村）", fontsize=7, color="#8a8984")
fig.savefig(FIG / "t2_entropy.png"); plt.close(fig)

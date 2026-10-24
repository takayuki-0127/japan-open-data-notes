"""2015年度から2021年度に、交通量が増えた道路・減った道路は？（道路交通センサス 都道府県×道路種別）"""
from common import *

d = load("traffic_census_pref_road.csv")
d["vol_chg"] = d.vol21 / d.vol15 - 1; d["vkm_chg"] = d.vkm21 / d.vkm15 - 1; d["len_chg"] = d.len21 / d.len15 - 1
d["large_diff"] = d.large21 - d.large15
d.to_csv(RES / "a171_changes.csv", index=False)
n = d[d.pref == "全国"].set_index("road"); p = d[d.pref != "全国"]
R = ["高速道路計", "一般国道計", "地方道計", "合計"]; RN = {"高速道路計": "高速道路", "一般国道計": "一般国道", "地方道計": "地方道（都道府県道など）", "合計": "合計"}
L = []
for r in R:
    x = n.loc[r]
    L.append(f"全国 {RN[r]}: 延長 {x.len15:,.0f}→{x.len21:,.0f}km（{x.len_chg:+.1%}） 24時間平均交通量 {x.vol15:,}→{x.vol21:,}台/日（{x.vol_chg:+.1%}） 走行台キロ {x.vkm_chg:+.1%} 大型車混入率 {x.large15}→{x.large21}%")
for r in R:
    q = p[p.road == r]
    L.append(f"{RN[r]} 都道府県の走行台キロの変化: 中央値 {q.vkm_chg.median():+.1%} 増えた県 {int((q.vkm_chg>0).sum())}/47 最大 {q.loc[q.vkm_chg.idxmax(),'pref']} {q.vkm_chg.max():+.1%} 最小 {q.loc[q.vkm_chg.idxmin(),'pref']} {q.vkm_chg.min():+.1%}")
cells = p[p.road != "合計"]
L.append(f"都道府県×道路種別141のうち、走行台キロが増えたのは {int((cells.vkm_chg>0).sum())}：" + "、".join(f"{a.pref}{RN[a.road]}{a.vkm_chg:+.1%}" for a in cells[cells.vkm_chg > 0].sort_values('vkm_chg', ascending=False).itertuples()))
h = p[p.road == "高速道路計"]
L.append(f"高速：延長の伸びと走行台キロの変化の相関 {h.len_chg.corr(h.vkm_chg):.2f}、延長の伸びと平均交通量の変化の相関 {h.len_chg.corr(h.vol_chg):.2f}、延長が5%以上伸びた県 {int((h.len_chg>=0.05).sum())} 平均交通量の変化 中央値 {h[h.len_chg>=0.05].vol_chg.median():+.1%}（それ以外 {h[h.len_chg<0.05].vol_chg.median():+.1%}）")
L.append(f"高速 大型車混入率が上がった県 {int((h.large_diff>0).sum())}/47、中央値 {h.large_diff.median():+.1f}ポイント 最大 {h.loc[h.large_diff.idxmax(),'pref']} {h.large_diff.max():+.1f}")
(RES / "a171_summary.txt").write_text("\n".join(L), encoding="utf-8"); print("\n".join(L))

fig, ax = plt.subplots(figsize=(9.5, 4.2))
xs = np.arange(len(R)); w = 0.26
for i, (c, lab, col) in enumerate([("len_chg", "延長", GRAY), ("vol_chg", "24時間平均交通量", BLUE), ("vkm_chg", "走行台キロ（交通量×延長）", ORANGE)]):
    v = [n.loc[r, c] * 100 for r in R]; ax.bar(xs + (i - 1) * w, v, w, color=col, label=lab)
    for xx, vv in zip(xs + (i - 1) * w, v): ax.text(xx, vv + (0.3 if vv >= 0 else -0.9), f"{vv:+.1f}", ha="center", fontsize=8)
ax.axhline(0, color=INK, lw=0.6); ax.set_xticks(xs); ax.set_xticklabels([RN[r] for r in R]); ax.set_ylabel("2015→2021年度の変化（%）")
ax.legend(frameon=False, fontsize=9, loc="upper right"); ax.set_title("全国の道路交通の変化（2015年度→2021年度）")
save(fig, "a171_national.png")

fig, ax = plt.subplots(figsize=(9.5, 4.6))
cols = {"高速道路計": ORANGE, "一般国道計": BLUE, "地方道計": GREEN}
for i, r in enumerate(cols):
    q = p[p.road == r].vkm_chg * 100
    ax.scatter(q, np.random.default_rng(i).uniform(-0.25, 0.25, len(q)) + i, s=22, color=cols[r], alpha=0.8)
    ax.plot([q.median()] * 2, [i - 0.35, i + 0.35], color=INK, lw=2)
ax.axvline(0, color=GRAY, lw=0.8, ls=":"); ax.set_yticks(range(3)); ax.set_yticklabels([RN[r] for r in cols])
ax.set_xlabel("走行台キロの変化（%、1つの点が1都道府県、黒い線は中央値）")
for r, (i, nm) in zip(cols, enumerate(cols)):
    q = p[p.road == r]; top = q.loc[q.vkm_chg.idxmax()]
    ax.annotate(top.pref, (top.vkm_chg * 100, i), xytext=(4, 6), textcoords="offset points", fontsize=8)
ax.set_title("都道府県ごとの走行台キロの変化の分布")
save(fig, "a171_distribution.png")

fig, ax = plt.subplots(figsize=(9.5, 4.4))
ax.scatter(h.len_chg * 100, h.vkm_chg * 100, color=ORANGE, s=30)
for a in h.itertuples():
    if a.len_chg > 0.10 or a.vkm_chg > 0.07 or a.vkm_chg < -0.15: ax.annotate(a.pref, (a.len_chg * 100, a.vkm_chg * 100), xytext=(3, 3), textcoords="offset points", fontsize=8)
ax.axhline(0, color=GRAY, lw=0.6, ls=":"); ax.axvline(0, color=GRAY, lw=0.6, ls=":")
ax.set_xlabel("高速道路の延長の変化（%）"); ax.set_ylabel("高速道路の走行台キロの変化（%）")
ax.set_title(f"高速道路の延長と走行台キロ（都道府県、相関 {h.len_chg.corr(h.vkm_chg):.2f}）")
save(fig, "a171_highway.png")

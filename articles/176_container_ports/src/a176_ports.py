"""外貿コンテナ取扱個数（TEU）の港ランキングは、2009〜2024年でどう変わったか"""
from common import *

d = load("major_ports.csv"); nat = load("national_total.csv")
d["teu"] = d.export_teu + d.import_teu
nat["teu"] = nat.export_teu + nat.import_teu
p = d.pivot(index="year", columns="port", values="teu")
rank = p.rank(axis=1, ascending=False, method="min").astype(int)
share = p.div(nat.set_index("year").teu, axis=0)
y0, y1 = p.index.min(), p.index.max()
L = []
L.append(f"全国の外貿コンテナ（輸出＋輸入、TEU） {y0} {nat.teu.iloc[0]/1e4:,.0f}万 → 2019 {nat.set_index('year').teu[2019]/1e4:,.0f}万 → {y1} {nat.teu.iloc[-1]/1e4:,.0f}万（{nat.teu.iloc[-1]/nat.teu.iloc[0]-1:+.1%}、2019比 {nat.teu.iloc[-1]/nat.set_index('year').teu[2019]-1:+.1%}）")
for y in [y0, 2019, y1]:
    s = p.loc[y].sort_values(ascending=False)
    L.append(f"{y} 上位: " + "、".join(f"{i+1}{k}{v/1e4:.0f}万" for i, (k, v) in enumerate(s.head(10).items())))
g = (p.loc[y1] / p.loc[y0] - 1).sort_values(ascending=False)
L.append("2009→2024 伸び率: " + "、".join(f"{k}{v:+.0%}" for k, v in g.items()))
g19 = (p.loc[y1] / p.loc[2019] - 1).sort_values(ascending=False)
L.append("2019→2024: " + "、".join(f"{k}{v:+.0%}" for k, v in g19.items()))
grp = pd.DataFrame({"京浜（東京＋横浜＋川崎）": p[["東京", "横浜", "川崎"]].sum(axis=1), "阪神（大阪＋神戸）": p[["大阪", "神戸"]].sum(axis=1), "名古屋": p["名古屋"]})
gs = grp.div(nat.set_index("year").teu, axis=0)
gs["五大港の計"] = gs.sum(axis=1)
L.append("割合 " + "；".join(f"{c}: {gs[c].iloc[0]:.1%}→{gs[c].iloc[-1]:.1%}" for c in gs.columns))
L.append("順位の変化（2009→2024）: " + "、".join(f"{k}{rank.loc[y0,k]}→{rank.loc[y1,k]}" for k in p.loc[y1].sort_values(ascending=False).index))
L.append(f"東京の輸入/輸出 {y1}: {d[(d.year==y1)&(d.port=='東京')].import_teu.iloc[0]/d[(d.year==y1)&(d.port=='東京')].export_teu.iloc[0]:.2f}")
L.append(f"清水 2018 {p.loc[2018,'清水']/1e4:.1f}万 → {y1} {p.loc[y1,'清水']/1e4:.1f}万；博多 2019 {p.loc[2019,'博多']/1e4:.1f}万 → {y1} {p.loc[y1,'博多']/1e4:.1f}万")
rank.to_csv(RES / "a176_rank.csv"); share.round(4).to_csv(RES / "a176_share.csv"); gs.round(4).to_csv(RES / "a176_group_share.csv")
(RES / "a176_summary.txt").write_text("\n".join(L), encoding="utf-8"); print("\n".join(L))

# 図1 上位10港の順位（2024年の上位10港）
top = p.loc[y1].sort_values(ascending=False).head(10).index
fig, ax = plt.subplots(figsize=(10, 5.2))
cols = [BLUE, ORANGE, GREEN, PURPLE, "#c94f7c", INK, "#8c6d31", LIGHT, GRAY, "#e3b23c"]
for c, k in zip(cols, top):
    ax.plot(rank.index, rank[k], marker="o", ms=3.5, lw=2, color=c)
    ax.text(y1 + 0.3, rank.loc[y1, k], f"{k}", va="center", fontsize=10, color=c)
    ax.text(y0 - 0.3, rank.loc[y0, k], f"{k}", va="center", ha="right", fontsize=9, color=c)
ax.invert_yaxis(); ax.set_yticks(range(1, 12)); ax.set_ylim(11.5, 0.5); ax.set_xlim(y0 - 2.2, y1 + 2.2)
ax.set_xticks(range(y0, y1 + 1, 3)); ax.set_ylabel("順位（外貿コンテナ個数）"); ax.set_title("外貿コンテナ取扱個数の港の順位（2024年の上位10港）")
save(fig, "a176_rank.png")

# 図2 五大港のシェア
fig, ax = plt.subplots(figsize=(10, 4.4))
for c, col in zip(gs.columns[:3], [BLUE, ORANGE, GREEN]):
    ax.plot(gs.index, gs[c] * 100, lw=2.2, color=col, label=c)
ax.plot(gs.index, gs["五大港の計"] * 100, lw=2.2, color=INK, ls="--", label="三つの合計")
ax.set_ylabel("全国の外貿コンテナに占める割合（%）"); ax.set_ylim(0, 85); ax.legend(frameon=False, ncol=2, fontsize=9)
ax.set_title("京浜・阪神・名古屋の割合")
save(fig, "a176_share.png")

# 図3 伸び率
fig, ax = plt.subplots(figsize=(10, 5))
gg = g.sort_values()
ax.barh(gg.index, np.minimum(gg.values, 0.6) * 100, color=[ORANGE if v < 0 else BLUE for v in gg.values])
for i, v in enumerate(gg.values):
    ax.text(min(v, 0.6) * 100 + (1 if v >= 0 else -1), i, f"{v:+.0%}" + ("（軸は60%で切っている）" if v > 0.6 else ""), va="center", ha="left" if v >= 0 else "right", fontsize=9)
ax.set_xlim(-60, 100)
ax.axvline(0, color=GRAY, lw=1); ax.set_xlabel("2009→2024年の増減（%）")
ax.set_title("主要17港の外貿コンテナ個数の増減（2009→2024年）")
save(fig, "a176_growth.png")

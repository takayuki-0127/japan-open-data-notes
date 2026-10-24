"""定期と定期外、コロナ後に戻らなかったのはどちらか（鉄道輸送統計調査 年報、2018〜2024年度）"""
from common import *

d = load("rail_passengers_fy.csv")
d["trip_km"] = d.passenger_km_million / d.passengers_million
p = d.pivot_table(index="fiscal_year", columns=["segment", "ticket"], values="passengers_million")
k = d.pivot_table(index="fiscal_year", columns=["segment", "ticket"], values="passenger_km_million")
idx = p / p.loc[2019] * 100
idx.round(1).to_csv(RES / "a181_index_fy2019_100.csv", encoding="utf-8")
L = []
for t in ["定期", "定期外"]:
    L.append(f"全体 {t}: " + "、".join(f"{y} {p.loc[y,('全体',t)]:,.0f}百万人（{idx.loc[y,('全体',t)]:.1f}）" for y in p.index))
L.append("2024年度の2019年度比（人数）: " + "、".join(f"{s}{t} {idx.loc[2024,(s,t)]:.1f}" for s in ["全体", "JR", "民鉄", "新幹線"] for t in ["定期", "定期外"]))
L.append("2024年度の2019年度比（人キロ）: " + "、".join(f"{s}{t} {k.loc[2024,(s,t)]/k.loc[2019,(s,t)]*100:.1f}" for s in ["全体", "JR", "民鉄", "新幹線"] for t in ["定期", "定期外"]))
low = {t: idx[("全体", t)].min() for t in ["定期", "定期外"]}
L.append(f"最も落ちた年度の水準: 定期 {low['定期']:.1f}、定期外 {low['定期外']:.1f}（2020年度）")
sh = p[("全体", "定期")] / (p[("全体", "定期")] + p[("全体", "定期外")]) * 100
L.append("人数に占める定期の割合: " + "、".join(f"{y} {sh[y]:.1f}%" for y in sh.index))
tk = d[d.segment == "全体"].pivot(index="fiscal_year", columns="ticket", values="trip_km")
L.append("1人1回の平均乗車キロ: " + "、".join(f"{y} 定期{tk.loc[y,'定期']:.1f}・定期外{tk.loc[y,'定期外']:.1f}" for y in tk.index))
gap = p.loc[2019] - p.loc[2024]
L.append(f"2019→2024年度に減った人数: 定期 {gap[('全体','定期')]:,.0f}百万人、定期外 {gap[('全体','定期外')]:,.0f}百万人")
(RES / "a181_summary.txt").write_text("\n".join(L), encoding="utf-8")
tk.round(2).to_csv(RES / "a181_trip_km.csv", encoding="utf-8")
print("\n".join(L))

# 図1：定期・定期外の旅客数の指数（2019年度=100）
fig, ax = plt.subplots(figsize=(9.5, 4.4))
for t, c in [("定期", BLUE), ("定期外", ORANGE)]:
    ax.plot(idx.index, idx[("全体", t)], marker="o", color=c, lw=2.4, label=f"{t}")
    ax.text(2024.1, idx.loc[2024, ("全体", t)], f"{idx.loc[2024,('全体',t)]:.1f}", color=c, va="center", fontsize=10)
ax.axhline(100, color=GRAY, lw=0.8, ls="--")
ax.set_ylim(55, 110); ax.set_xticks(idx.index); ax.set_xticklabels([f"{y}年度" for y in idx.index], fontsize=9)
ax.set_ylabel("2019年度＝100"); ax.legend(frameon=False, loc="lower right")
ax.set_title("鉄道の旅客数（人数）：定期と定期外")
save(fig, "a181_index.png")

# 図2：区分別の2024年度の戻り（2019年度=100）
segs = ["JR", "民鉄", "新幹線"]
fig, ax = plt.subplots(figsize=(9.5, 4.2))
x = np.arange(len(segs)); w = 0.36
for j, (t, c) in enumerate([("定期", BLUE), ("定期外", ORANGE)]):
    v = [idx.loc[2024, (s, t)] for s in segs]
    ax.bar(x + (j - 0.5) * w, v, w, color=c, label=t)
    for xi, vi in zip(x, v):
        ax.text(xi + (j - 0.5) * w, vi + 1, f"{vi:.1f}", ha="center", fontsize=10)
ax.axhline(100, color=GRAY, lw=0.8, ls="--")
ax.set_xticks(x); ax.set_xticklabels(segs); ax.set_ylim(0, 130); ax.set_ylabel("2019年度＝100（人数）")
ax.legend(frameon=False, loc="upper left", ncol=2); ax.set_title("2024年度の旅客数の戻り（2019年度＝100）")
save(fig, "a181_segments.png")

# 図3：人数に占める定期の割合と、定期外の平均乗車キロ
fig, ax = plt.subplots(figsize=(9.5, 4.2))
ax.plot(sh.index, sh.values, marker="o", color=BLUE, lw=2.4, label="人数に占める定期の割合（左）")
ax.set_ylim(50, 66); ax.set_ylabel("%")
ax2 = ax.twinx(); ax2.spines["right"].set_visible(True)
ax2.plot(tk.index, tk["定期外"], marker="s", color=ORANGE, lw=2, label="定期外の1人1回の平均乗車キロ（右）")
ax2.set_ylim(14, 24); ax2.set_ylabel("km")
ax.set_xticks(sh.index); ax.set_xticklabels([f"{y}年度" for y in sh.index], fontsize=9)
h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
ax.legend(h1 + h2, l1 + l2, frameon=False, loc="upper right", fontsize=9)
ax.set_title("定期の割合と、定期外の平均乗車キロ")
save(fig, "a181_share_tripkm.png")

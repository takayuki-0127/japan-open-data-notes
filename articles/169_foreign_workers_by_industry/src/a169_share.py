"""外国人労働者が多い産業は、10年で入れ替わったのか（各年10月末、2016〜2025年）"""
from common import *

d = load("workers_by_industry_2016_2025.csv").set_index("industry")
Y = list(d.columns); yrs = [int(c[1:]) for c in Y]
tot = d.loc["総数"]; g = d.drop(index="総数")
print("内訳の合計と総数の差:", (g.sum() - tot).abs().max())
SH = {"サービス業（他に分類されないもの）": "サービス業（他に分類されないもの）", "宿泊業、飲食サービス業": "宿泊・飲食", "卸売業、小売業": "卸売・小売", "教育、学習支援業": "教育・学習支援", "医療、福祉": "医療・福祉"}
sh = g.div(tot) * 100
a, b = "y2016", "y2025"
t = pd.DataFrame({"n2016": g[a], "n2025": g[b], "times": g[b] / g[a], "share2016": sh[a], "share2025": sh[b], "share_pt": sh[b] - sh[a],
                  "rank2016": g[a].rank(ascending=False).astype(int), "rank2025": g[b].rank(ascending=False).astype(int)}).sort_values("n2025", ascending=False)
t.round(3).to_csv(RES / "a169_change_2016_2025.csv", encoding="utf-8")
sh.T.set_index(pd.Index(yrs)).round(3).to_csv(RES / "a169_share_by_year.csv", encoding="utf-8")
L = [f"総数 2016年 {tot[a]:,} → 2025年 {tot[b]:,}（{tot[b]/tot[a]:.2f}倍）", t.round(2).to_string()]
(RES / "a169_summary.txt").write_text("\n\n".join(L), encoding="utf-8"); print("\n\n".join(L))

# 図1：構成比（2016年と2025年）
fig, ax = plt.subplots(figsize=(9.5, 5.2))
o = t.sort_values("share2025"); idx = range(len(o))
ax.barh([i + 0.2 for i in idx], o.share2016, height=0.4, color=LIGHT, label="2016年")
ax.barh([i - 0.2 for i in idx], o.share2025, height=0.4, color=BLUE, label="2025年")
ax.set_yticks(list(idx)); ax.set_yticklabels([SH.get(n, n) for n in o.index])
for i, (s0, s1) in enumerate(zip(o.share2016, o.share2025)):
    ax.text(max(s0, s1) + 0.4, i, f"{s0:.1f}% → {s1:.1f}%", va="center", fontsize=8.5)
ax.set_xlim(0, 38); ax.set_xlabel("外国人労働者に占める割合（%、各年10月末）"); ax.legend(loc="lower right", frameon=False)
ax.set_title("製造業は1位のままだが31.2%から24.7%へ。順位の大きな入れ替わりはない")
save(fig, "a169_share_2016_2025.png")

# 図2：構成比の推移
fig, ax = plt.subplots(figsize=(9.5, 4.8))
keys = ["製造業", "サービス業（他に分類されないもの）", "卸売業、小売業", "宿泊業、飲食サービス業", "建設業", "医療、福祉"]
cols = [GRAY, PURPLE, BLUE, ORANGE, GREEN, "#c9a227"]
for k, c in zip(keys, cols):
    ax.plot(yrs, sh.loc[k].values, color=c, lw=2, marker="o", ms=3)
    ax.text(2025.2, sh.loc[k, "y2025"] + {"卸売業、小売業": 0.35, "宿泊業、飲食サービス業": -0.35}.get(k, 0), SH.get(k, k).replace("（他に分類されないもの）", ""), color=c, fontsize=8.5, va="center")
ax.set_xlim(2016, 2027.4); ax.set_xticks(range(2016, 2026, 1)); ax.set_ylabel("割合（%）")
ax.set_title("製造業の割合はほぼ一貫して下がり、建設業と医療・福祉が上がった")
save(fig, "a169_share_trend.png")

# 図3：2016年からの倍率
fig, ax = plt.subplots(figsize=(9.5, 4.6))
o = t.sort_values("times")
ax.barh([SH.get(n, n) for n in o.index], o.times, color=[ORANGE if x > tot[b] / tot[a] else BLUE for x in o.times])
for i, (x, n0, n1) in enumerate(zip(o.times, o.n2016, o.n2025)):
    ax.text(x + 0.06, i, f"{x:.1f}倍（{n0/1e4:.1f}万→{n1/1e4:.1f}万人）", va="center", fontsize=8.5)
ax.axvline(tot[b] / tot[a], color=INK, ls="--", lw=1); ax.text(tot[b] / tot[a] + 0.05, len(o) - 0.45, f"全体 {tot[b]/tot[a]:.1f}倍", fontsize=8.5)
ax.set_xlim(0, 10.8); ax.set_xlabel("2016年→2025年の倍率")
ax.set_title("医療・福祉は8.4倍、建設業は5.0倍。全体は2.4倍")
save(fig, "a169_growth.png")

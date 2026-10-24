"""177 受療率の都道府県差は、年齢をそろえても残るか（直接法による年齢調整）"""
from common import *

d = load("jyuryo_2023_pref_age.csv")
crude = d[d.age == "総数"].set_index("pref")
a = d[d.age != "総数"]
ages = list(a[a.pref == "全国"].age)
std = a[a.pref == "全国"].set_index("age").pop_thousand          # 基準人口＝全国の年齢構成
w = std / std.sum()
rows = []
for p, g in a.groupby("pref", sort=False):
    g = g.set_index("age").loc[ages]
    share65 = g.loc[["６５～７４", "７５～８４", "８５以上"]].pop_thousand.sum() / g.pop_thousand.sum()
    rows.append(dict(pref=p, inpatient_crude=crude.loc[p, "inpatient_per100k"], outpatient_crude=crude.loc[p, "outpatient_per100k"],
                     inpatient_adj=(g.inpatient_per100k * w).sum(), outpatient_adj=(g.outpatient_per100k * w).sum(), share65=share65))
r = pd.DataFrame(rows).set_index("pref")
nat = r.loc["全国"]; r = r.drop("全国")
for k in ["inpatient", "outpatient"]:
    r[k + "_crude_rank"] = r[k + "_crude"].rank(ascending=False).astype(int)
    r[k + "_adj_rank"] = r[k + "_adj"].rank(ascending=False).astype(int)
    r[k + "_adj_ratio"] = r[k + "_adj"] / nat[k + "_adj"]
r.round(3).to_csv(RES / "a177_adjusted.csv", encoding="utf-8-sig")

WEST = ["福岡", "佐賀", "長崎", "熊本", "大分", "宮崎", "鹿児島", "徳島", "香川", "愛媛", "高知", "山口"]
out = [f"全国 粗 入院{nat.inpatient_crude:.0f} 外来{nat.outpatient_crude:.0f} / 調整 入院{nat.inpatient_adj:.1f} 外来{nat.outpatient_adj:.1f}"]
for k in ["inpatient", "outpatient"]:
    for t in ["crude", "adj"]:
        s = r[f"{k}_{t}"]
        out.append(f"{k} {t}: max {s.idxmax()} {s.max():.0f} min {s.idxmin()} {s.min():.0f} ratio {s.max()/s.min():.2f} CV {s.std()/s.mean():.3f}")
    out.append(f"{k} top10 adj: " + ", ".join(f"{p}{v:.0f}" for p, v in r[f'{k}_adj'].nlargest(10).items()))
    out.append(f"{k} bottom5 adj: " + ", ".join(f"{p}{v:.0f}" for p, v in r[f'{k}_adj'].nsmallest(5).items()))
    out.append(f"{k} corr crude-adj {r[k+'_crude'].corr(r[k+'_adj']):.3f}; corr crude-share65 {r[k+'_crude'].corr(r.share65):.3f}; adj-share65 {r[k+'_adj'].corr(r.share65):.3f}")
    rc = (r[k+"_crude_rank"] - r[k+"_adj_rank"])
    out.append(f"{k} rank change up(adj higher): " + ", ".join(f"{p}{v:+d}" for p, v in rc.nlargest(5).items()) + " | down: " + ", ".join(f"{p}{v:+d}" for p, v in rc.nsmallest(5).items()))
    out.append(f"{k} 九州・四国・山口12県 mean adj {r.loc[WEST, k+'_adj'].mean():.0f} vs others {r.drop(WEST)[k+'_adj'].mean():.0f}; in top12 {r[k+'_adj'].nlargest(12).index.isin(WEST).sum()}")
out.append("share65 max " + r.share65.idxmax() + f" {r.share65.max():.3f} min " + r.share65.idxmin() + f" {r.share65.min():.3f}")
out.append("selected: " + "; ".join(f"{p} 入院 {r.loc[p,'inpatient_crude']:.0f}->{r.loc[p,'inpatient_adj']:.0f}(#{r.loc[p,'inpatient_crude_rank']}->#{r.loc[p,'inpatient_adj_rank']}) 外来 {r.loc[p,'outpatient_crude']:.0f}->{r.loc[p,'outpatient_adj']:.0f}(#{r.loc[p,'outpatient_crude_rank']}->#{r.loc[p,'outpatient_adj_rank']})" for p in ["高知", "鹿児島", "長崎", "秋田", "北海道", "東京", "神奈川", "沖縄", "埼玉", "愛知", "香川", "和歌山", "岐阜"]))
(RES / "a177_summary.txt").write_text("\n".join(out), encoding="utf-8"); print("\n".join(out))

# 図1 粗率と調整率（入院）
fig, ax = plt.subplots(figsize=(7.5, 6))
ax.scatter(r.inpatient_crude, r.inpatient_adj, color=[ORANGE if p in WEST else BLUE for p in r.index], s=28)
for p in r.index:
    if p in ["高知", "鹿児島", "長崎", "熊本", "山口", "佐賀", "秋田", "北海道", "東京", "神奈川", "埼玉", "沖縄", "長野", "島根", "愛知"]:
        ax.annotate(p, (r.loc[p, "inpatient_crude"], r.loc[p, "inpatient_adj"]), fontsize=8.5, xytext=(4, 2), textcoords="offset points")
lim = [550, 1850]; ax.plot(lim, lim, color=GRAY, lw=0.8, ls="--"); ax.text(1500, 1530, "粗率＝調整率", fontsize=8.5, color=GRAY)
ax.axhline(nat.inpatient_adj, color=GRAY, lw=0.6)
ax.set_xlim(lim); ax.set_ylim(lim)
ax.set_xlabel("そのままの入院受療率（人口10万対）"); ax.set_ylabel("年齢調整した入院受療率（人口10万対）")
ax.set_title("入院受療率：年齢をそろえても九州・四国・山口は高い（2023年）", loc="left")
ax.text(560, 1800, "オレンジ＝九州・四国・山口の12県", fontsize=8.5, color=ORANGE)
save(fig, "a177_inpatient_scatter.png")

# 図2 調整後の入院受療率の並び
s = r.inpatient_adj.sort_values()
fig, ax = plt.subplots(figsize=(7.5, 10))
ax.barh(s.index, s.values, color=[ORANGE if p in WEST else LIGHT for p in s.index])
ax.scatter(r.loc[s.index, "inpatient_crude"], s.index, color=INK, s=10, zorder=3, label="そのままの受療率")
ax.axvline(nat.inpatient_adj, color=GRAY, lw=0.8, ls="--"); ax.text(nat.inpatient_adj + 10, 0, f"全国 {nat.inpatient_adj:.0f}", fontsize=8.5, color=GRAY)
ax.set_xlabel("人口10万対"); ax.tick_params(axis="y", labelsize=8.5); ax.legend(loc="lower right", frameon=False, fontsize=9)
ax.set_title("年齢調整した入院受療率（棒）と、そのままの値（点）", loc="left")
save(fig, "a177_inpatient_rank.png")

# 図3 ばらつき：最大/最小の比
fig, ax = plt.subplots(figsize=(7, 4))
lab = ["入院", "外来"]; x = np.arange(2)
c = [r[f"{k}_crude"].max() / r[f"{k}_crude"].min() for k in ["inpatient", "outpatient"]]
j = [r[f"{k}_adj"].max() / r[f"{k}_adj"].min() for k in ["inpatient", "outpatient"]]
ax.bar(x - 0.2, c, 0.38, color=GRAY, label="そのまま"); ax.bar(x + 0.2, j, 0.38, color=BLUE, label="年齢調整後")
for i in range(2):
    ax.text(x[i] - 0.2, c[i] + 0.03, f"{c[i]:.2f}倍", ha="center", fontsize=9); ax.text(x[i] + 0.2, j[i] + 0.03, f"{j[i]:.2f}倍", ha="center", fontsize=9)
ax.set_xticks(x, lab); ax.set_ylim(1, max(c + j) + 0.4); ax.set_ylabel("最も高い県 ÷ 最も低い県")
ax.legend(frameon=False); ax.set_title("都道府県の差（最大÷最小）は、年齢をそろえても残る", loc="left")
save(fig, "a177_spread.png")

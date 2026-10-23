"""小学校の先生の年齢構成は「ふたコブ」からどう変わったか（1998〜2025年度、3年ごと）"""
from common import *

d = load()
ages = [str(a) for a in range(20, 60)]
tot = d.sum(axis=1)
share = d.div(tot, axis=0)
L = []
grp = pd.DataFrame({"20代": d[[str(a) for a in range(20, 30)]].sum(1) + d.le19, "30代": d[[str(a) for a in range(30, 40)]].sum(1),
                    "40代": d[[str(a) for a in range(40, 50)]].sum(1), "50代": d[[str(a) for a in range(50, 60)]].sum(1), "60歳以上": d["60plus"]})
gs = grp.div(tot, axis=0)
gs.to_csv(RES / "a148_age_group_share.csv", encoding="utf-8")
# 平均年齢（各歳の中央値、60歳以上は62歳とみなす）
mid = {**{str(a): a + 0.5 for a in range(20, 60)}, "le19": 19.5, "60plus": 62.0}
mean = (d[list(mid)] * pd.Series(mid)).sum(1) / tot
# 2つの山：25〜39歳での最大と、40〜59歳での最大
peaks = []
for y in d.index:
    r = d.loc[y, ages].astype(float)
    young = r[[str(a) for a in range(23, 40)]]; old = r[[str(a) for a in range(40, 60)]]
    valley = r[[str(a) for a in range(30, 50)]]
    peaks.append(dict(year=y, young_peak_age=int(young.idxmax()), young_peak=int(young.max()),
                      old_peak_age=int(old.idxmax()), old_peak=int(old.max()), valley_age=int(valley.idxmin()), valley=int(valley.min()), total=int(tot[y]), mean_age=round(mean[y], 1)))
pk = pd.DataFrame(peaks).set_index("year"); pk.to_csv(RES / "a148_peaks.csv", encoding="utf-8")
for y in d.index:
    L.append(f"{y}年度 計 {tot[y]:,}人 平均年齢(目安) {mean[y]:.1f}歳 20代 {gs.loc[y,'20代']:.1%} 30代 {gs.loc[y,'30代']:.1%} 40代 {gs.loc[y,'40代']:.1%} 50代 {gs.loc[y,'50代']:.1%} 60+ {gs.loc[y,'60歳以上']:.1%} | 若い山 {pk.loc[y,'young_peak_age']}歳 {pk.loc[y,'young_peak']:,} 上の山 {pk.loc[y,'old_peak_age']}歳 {pk.loc[y,'old_peak']:,} 谷 {pk.loc[y,'valley_age']}歳 {pk.loc[y,'valley']:,}")
# 1966年（丙午）生まれの谷：1998年度 32歳
L.append(f"1998年度 31歳 {d.loc[1998,'31']:,} / 32歳 {d.loc[1998,'32']:,} / 33歳 {d.loc[1998,'33']:,}（1966年生まれの谷）")
L.append(f"22〜24歳（新卒世代）: 1998 {d.loc[1998,['22','23','24']].sum():,} → 2001 {d.loc[2001,['22','23','24']].sum():,} → 2025 {d.loc[2025,['22','23','24']].sum():,}")
L.append(f"60歳以上: 1998 {d.loc[1998,'60plus']:,} → 2025 {d.loc[2025,'60plus']:,}")
(RES / "a148_summary.txt").write_text("\n".join(L), encoding="utf-8")
print("\n".join(L))

# 図1：年齢別の人数（4時点）
fig, ax = plt.subplots(figsize=(9.5, 4.6))
x = np.arange(20, 60)
for y, col, lw in [(1998, GRAY, 1.6), (2007, LIGHT, 1.8), (2016, ORANGE, 2.0), (2025, BLUE, 2.6)]:
    ax.plot(x, d.loc[y, ages].values / 1000, color=col, lw=lw, label=f"{y}年度")
ax.set_xlabel("年齢（歳）"); ax.set_ylabel("先生の数（千人）"); ax.set_xticks(range(20, 61, 5))
ax.legend(frameon=False, fontsize=9.5, loc="upper left")
for y, a in [(1998, 32), (2007, 41), (2016, 50)]:
    ax.annotate("", xy=(a, d.loc[y, str(a)] / 1000 - 0.15), xytext=(a, d.loc[y, str(a)] / 1000 - 1.6), arrowprops=dict(arrowstyle="->", color=INK, lw=0.9))
ax.text(41, 7.6, "1966年生まれの谷\n（1998年度32歳→2007年度41歳→2016年度50歳）", fontsize=8.5, color=INK, ha="center", va="top")
ax.set_title("小学校の先生の年齢別人数（本務教員、国公私立計）")
save(fig, "a148_curves.png")

# 図2：年代の割合
fig, ax = plt.subplots(figsize=(9.5, 4.4))
cols = {"20代": BLUE, "30代": LIGHT, "40代": GRAY, "50代": ORANGE, "60歳以上": PURPLE}
bottom = np.zeros(len(gs)); xs = np.arange(len(gs))
for c, col in cols.items():
    v = gs[c].values * 100
    ax.bar(xs, v, bottom=bottom, color=col, width=0.7, label=c)
    for xi, (b, vv) in enumerate(zip(bottom, v)):
        if vv >= 7: ax.text(xi, b + vv / 2, f"{vv:.0f}", ha="center", va="center", fontsize=8.5, color="white" if c != "40代" else INK)
    bottom += v
ax.set_xticks(xs); ax.set_xticklabels([f"{y}" for y in gs.index]); ax.set_xlabel("調査年度")
ax.set_ylabel("割合（%）"); ax.set_ylim(0, 100)
ax.legend(frameon=False, fontsize=9, loc="center left", bbox_to_anchor=(1.0, 0.5), reverse=True)
ax.set_title("小学校の先生の年代別の割合")
save(fig, "a148_groups.png")

# 図3：年齢×年度のヒートマップ（山が右へ動いていく）
fig, ax = plt.subplots(figsize=(9.5, 4.4))
m = share[ages].values * 100
im = ax.imshow(m, aspect="auto", cmap="Blues", origin="upper", extent=[19.5, 59.5, len(d) - 0.5, -0.5])
ax.set_yticks(range(len(d))); ax.set_yticklabels(d.index)
ax.set_xticks(range(20, 61, 5)); ax.set_xlabel("年齢（歳）"); ax.set_ylabel("調査年度")
for i, y in enumerate(d.index):
    ax.plot(pk.loc[y, "old_peak_age"], i, "o", color=ORANGE, ms=5)
cb = fig.colorbar(im, ax=ax, fraction=0.03); cb.set_label("その年度の先生に占める割合（%）")
ax.set_title("年齢ごとの割合：●（40〜59歳で最も多い年齢）は右へ動き、50代後半で退職へ")
save(fig, "a148_heatmap.png")

"""180 日本の輸出相手国のランキングは30年でどう変わったか"""
from common import *

d = load("exports_by_country_1995_2025.csv")
tot = load("exports_total_1995_2025.csv").set_index("year").export_total_million_yen
w = d.pivot(index="year", columns="country", values="export_million_yen")
rank = w.rank(axis=1, ascending=False, method="min").astype(int)
share = w.div(tot, axis=0) * 100
rank.to_csv(RES / "a180_rank.csv", encoding="utf-8-sig"); share.round(2).to_csv(RES / "a180_share.csv", encoding="utf-8-sig")

R = []
R.append(f"total 1995 {tot[1995]/1e6:.1f}兆 2025 {tot[2025]/1e6:.1f}兆 ({tot[2025]/tot[1995]:.2f}倍)")
for y in [1995, 2005, 2015, 2025]:
    s = w.loc[y].sort_values(ascending=False).head(12)
    R.append(f"{y} top12: " + ", ".join(f"{k}{v/1e4:.1f}千億({share.loc[y,k]:.1f}%)" for k, v in s.items()))
first = rank.idxmin(axis=1)
R.append("1位: " + ", ".join(f"{y}{first[y]}" for y in rank.index if y == 1995 or first[y] != first[y - 1]))
R.append("中国1位の年: " + ",".join(str(y) for y in rank.index if first[y] == "中国"))
R.append("米国 share: " + ", ".join(f"{y}:{share.loc[y,'米国']:.1f}" for y in [1995, 2000, 2005, 2009, 2010, 2015, 2020, 2025]))
R.append("中国 share: " + ", ".join(f"{y}:{share.loc[y,'中国']:.1f}" for y in [1995, 2000, 2005, 2009, 2010, 2015, 2020, 2025]))
for c in ["中国", "ベトナム", "インド", "アラブ首長国連邦", "メキシコ", "英国", "シンガポール", "マレーシア", "インドネシア", "ドイツ", "オランダ", "香港", "台湾", "韓国", "タイ", "オーストラリア"]:
    R.append(f"{c}: rank {min(rank.loc[1995,c],21)}→{min(rank.loc[2005,c],21)}→{rank.loc[2015,c]}→{rank.loc[2025,c]}, 金額 {w.loc[1995,c]/w.loc[2025,c]**0:.0f}→{w.loc[2025,c]:.0f} ({w.loc[2025,c]/w.loc[1995,c]:.1f}倍), share {share.loc[1995,c]:.1f}→{share.loc[2025,c]:.1f}")
t10_95 = set(rank.loc[1995][rank.loc[1995] <= 10].index); t10_25 = set(rank.loc[2025][rank.loc[2025] <= 10].index)
R.append(f"top10 1995 only: {t10_95 - t10_25}; 2025 only: {t10_25 - t10_95}; both {len(t10_95 & t10_25)}")
asia = ["中国", "韓国", "台湾", "香港", "シンガポール", "タイ", "マレーシア", "インドネシア", "フィリピン", "ベトナム", "インド"]
R.append("asia11 share: " + ", ".join(f"{y}:{share.loc[y,asia].sum():.1f}" for y in [1995, 2005, 2015, 2025]))
eu = ["ドイツ", "英国", "オランダ", "フランス", "ベルギー", "イタリア"]
R.append("europe6 share: " + ", ".join(f"{y}:{share.loc[y,eu].sum():.1f}" for y in [1995, 2005, 2015, 2025]))
R.append("top2 share: " + ", ".join(f"{y}:{share.loc[y,['米国','中国']].sum():.1f}" for y in [1995, 2005, 2015, 2025]))
R.append(f"US 2025 vs 2024: {w.loc[2025,'米国']/w.loc[2024,'米国']*100-100:.1f}%  China {w.loc[2025,'中国']/w.loc[2024,'中国']*100-100:.1f}%  total {tot[2025]/tot[2024]*100-100:.1f}%")
(RES / "a180_summary.txt").write_text("\n".join(R), encoding="utf-8"); print("\n".join(R))

# 図1 順位の推移（バンプチャート）
show = sorted(set(rank.columns[(rank.loc[[1995, 2005, 2015, 2025]] <= 10).any()]), key=lambda c: rank.loc[2025, c])
hl = {"米国": BLUE, "中国": ORANGE, "ベトナム": GREEN, "インド": PURPLE, "台湾": "#c9302c", "シンガポール": "#8a6d3b"}
fig, ax = plt.subplots(figsize=(9, 6))
for c in show:
    col = hl.get(c, LIGHT); lw = 2.4 if c in hl else 1.3
    ax.plot(rank.index, rank[c].clip(upper=21), color=col, lw=lw, zorder=3 if c in hl else 2)
    ax.text(2025.4, rank.loc[2025, c], f"{rank.loc[2025,c]} {c}", va="center", fontsize=8.5, color=col if c in hl else GRAY)
    if rank.loc[1995, c] <= 20: ax.text(1994.6, rank.loc[1995, c], c, va="center", ha="right", fontsize=8, color=col if c in hl else GRAY)
ax.set_ylim(21.5, 0.5); ax.set_yticks([1, 5, 10, 15, 20]); ax.set_xlim(1991, 2030)
ax.set_ylabel("輸出額の順位"); ax.set_title("日本の輸出相手国の順位（1995〜2025年、いずれかの節目年に10位以内）", loc="left")
ax.text(1995.3, 19.6, "ベトナム・インドは1995年に21位以下\n（21位以下は21位の位置に表示）", fontsize=8, color=GRAY)
save(fig, "a180_bump.png")

# 図2 米国・中国・アジア・欧州の割合
fig, ax = plt.subplots(figsize=(8, 4.5))
ax.plot(share.index, share["米国"], color=BLUE, lw=2.2, label="米国")
ax.plot(share.index, share["中国"], color=ORANGE, lw=2.2, label="中国")
ax.plot(share.index, share[["韓国", "台湾", "香港"]].sum(axis=1), color=PURPLE, lw=1.6, label="韓国・台湾・香港")
ax.plot(share.index, share[["シンガポール", "タイ", "マレーシア", "インドネシア", "フィリピン", "ベトナム"]].sum(axis=1), color=GREEN, lw=1.6, label="ASEAN6か国")
ax.plot(share.index, share[eu].sum(axis=1), color=GRAY, lw=1.6, label="欧州6か国")
ax.set_ylabel("輸出総額に占める割合（%）"); ax.set_ylim(0, 32); ax.legend(frameon=False, ncol=3, fontsize=8.5, loc="upper right")
ax.set_title("輸出先の割合：米国と中国（1995〜2025年）", loc="left")
save(fig, "a180_share.png")

# 図3 1995年と2025年の上位15か国（スロープ）
fig, ax = plt.subplots(figsize=(7, 7))
cs = sorted(set(rank.columns[(rank.loc[[1995, 2025]] <= 15).any()]))
for c in cs:
    a, b = min(rank.loc[1995, c], 21), min(rank.loc[2025, c], 21)
    col = GREEN if b < a - 2 else (ORANGE if b > a + 2 else GRAY)
    ax.plot([0, 1], [a, b], color=col, lw=1.8, marker="o", ms=4)
    if a <= 20: ax.text(-0.04, a, f"{c} {a}", ha="right", va="center", fontsize=8.5, color=col)
    ax.text(1.04, b, f"{b if b <= 20 else '21位以下'} {c}", ha="left", va="center", fontsize=8.5, color=col)
ax.set_ylim(22, 0); ax.set_xlim(-0.6, 1.6)
ax.set_xticks([0, 1], ["1995年", "2025年"]); ax.set_yticks([]); ax.spines["left"].set_visible(False)
ax.set_title("1995年と2025年の順位（どちらかで15位以内）", loc="left")
ax.text(-0.04, 21, "インド・ベトナム・\nアラブ首長国連邦 21位以下", ha="right", va="center", fontsize=8.5, color=GREEN)
ax.text(-0.55, 0.2, "緑＝3つ以上上がった、オレンジ＝3つ以上下がった", fontsize=8, color=GRAY)
save(fig, "a180_slope.png")

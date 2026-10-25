"""223 ネットで買う品目の順位は10年でどう入れ替わったか（家計消費状況調査 22品目、2015〜2025年）"""
from common import *
from scipy.stats import spearmanr, kendalltau

d, t = load()
v = d.set_index("item")[YEARS]
rank = v.rank(ascending=False, method="min").astype(int)
share = v / v.sum() * 100

# 1) 順位表と変化
out = pd.DataFrame({"code": d.code.values, "group": d.group.values}, index=v.index)
for y in ["2015", "2019", "2020", "2025"]:
    out["rank_" + y] = rank[y]
out["yen_2015"], out["yen_2025"] = v["2015"], v["2025"]
out["ratio_2025_2015"] = (v["2025"] / v["2015"]).round(2)
out["share_2015"], out["share_2025"] = share["2015"].round(1), share["2025"].round(1)
out["rank_change"] = out.rank_2015 - out.rank_2025
out.sort_values("rank_2025").to_csv(RES / "rank_2015_2025.csv")

# 2) 順位の相関（前年比・2015年比）
rows = []
for i, y in enumerate(YEARS[1:], 1):
    rows.append({"year": y, "spearman_vs_prev": spearmanr(v[YEARS[i - 1]], v[y])[0],
                 "spearman_vs_2015": spearmanr(v["2015"], v[y])[0],
                 "kendall_vs_2015": kendalltau(v["2015"], v[y])[0],
                 "top5_same_as_2015": len(set(rank.index[rank["2015"] <= 5]) & set(rank.index[rank[y] <= 5]))})
corr = pd.DataFrame(rows).round(3)
corr.to_csv(RES / "rank_correlation.csv", index=False)

# 3) 総額の増加に対する品目の寄与
inc = (v["2025"] - v["2015"])
contrib = (inc / inc.sum() * 100).round(1).sort_values(ascending=False)
pd.DataFrame({"increase_yen": inc, "contribution_pct": contrib}).sort_values("contribution_pct", ascending=False).to_csv(RES / "contribution_2015_2025.csv")

print(out.sort_values("rank_2025")[["rank_2015", "rank_2025", "rank_change", "yen_2015", "yen_2025", "ratio_2025_2015", "share_2015", "share_2025"]])
print(corr)
print(contrib.head(6))

# 図1 順位の入れ替わり（バンプチャート）
fig, ax = plt.subplots(figsize=(9, 8.5))
xs = np.arange(len(YEARS))
hi = {"食料品": ORANGE, "出前": "#c0392b", "飲料": "#e8a33d", "旅行（ネット上で決済）": BLUE, "チケット": PURPLE, "家電": GREEN, "書籍": INK, "音楽・映像・ゲームソフト": "#6b4f2a"}
for it in v.index:
    c = hi.get(it, LIGHT); lw = 2.6 if it in hi else 1.0
    ax.plot(xs, rank.loc[it], color=c, lw=lw, marker="o", ms=3.5 if it in hi else 2, zorder=3 if it in hi else 1)
    ax.text(-0.15, rank.loc[it, "2015"], it, ha="right", va="center", fontsize=8, color=c if it in hi else GRAY)
    ax.text(len(YEARS) - 0.85, rank.loc[it, "2025"], f"{rank.loc[it,'2025']} {it}", ha="left", va="center", fontsize=8, color=c if it in hi else GRAY)
ax.set_ylim(22.7, 0.3); ax.set_xlim(-3.6, len(YEARS) + 2.6)
ax.set_xticks(xs); ax.set_xticklabels(YEARS, fontsize=9)
ax.set_yticks([]); ax.spines["left"].set_visible(False)
ax.set_title("ネットショッピングの支出額の順位（22品目、二人以上の世帯）", loc="left")
save(fig, "a223_bump.png")

# 図2 2015→2025の倍率と金額
o = out.sort_values("ratio_2025_2015")
fig, ax = plt.subplots(figsize=(8, 7.5))
cols = [ORANGE if g == "食料" else BLUE if g == "旅行関係費" else GRAY for g in o.group]
ax.barh(o.index, o.ratio_2025_2015, color=cols)
for i, (r, a, b) in enumerate(zip(o.ratio_2025_2015, o.yen_2015, o.yen_2025)):
    ax.text(r + 0.15, i, f"{r:.1f}倍（{a:,}→{b:,}円）", va="center", fontsize=8.5)
ax.axvline(t.loc[2025, "total_22"] / t.loc[2015, "total_22"], color=INK, lw=1, ls="--")
ax.text(t.loc[2025, "total_22"] / t.loc[2015, "total_22"] + 0.1, -1.1, f"22品目計 {t.loc[2025,'total_22']/t.loc[2015,'total_22']:.1f}倍", fontsize=8.5)
ax.set_xlim(0, 17); ax.set_xlabel("2025年 ÷ 2015年（月平均支出額）")
ax.set_title("2015→2025年に何倍になったか（オレンジ＝食料、青＝旅行関係）", loc="left")
save(fig, "a223_ratio.png")

# 図3 構成比の推移（主なグループ）
g = d.groupby("group")[YEARS].sum()
gs = g / g.sum() * 100
main = {"食料": (ORANGE, 0.9), "旅行関係費": (BLUE, -0.9), "その他": (GRAY, 0), "衣類・履物": ("#e8a33d", 0.55),
        "教養": (PURPLE, -0.55), "家電・家具": (GREEN, 0)}
fig, ax = plt.subplots(figsize=(9, 5.2))
yrs = [int(y) for y in YEARS]
for k in gs.index:
    if k not in main:
        ax.plot(yrs, gs.loc[k], color=LIGHT, lw=1)
for k, (c, off) in main.items():
    ax.plot(yrs, gs.loc[k], color=c, lw=2.6 if k in ("食料", "旅行関係費") else 1.6, marker="o", ms=3)
    ax.text(2025.25, gs.loc[k, "2025"] + off, f"{k} {gs.loc[k,'2025']:.1f}%", va="center", fontsize=9, color=c)
ax.text(2025.25, 4.0, "保健・医療／保険／\n贈答品（各3〜5%）", va="center", fontsize=8, color=GRAY)
ax.set_xlim(2014.6, 2027.6); ax.set_xticks(yrs[::2]); ax.set_ylabel("22品目計に占める割合（%）")
ax.set_title("ネットショッピングの支出の構成比（9グループ）", loc="left")
save(fig, "a223_share.png")
g.round(0).to_csv(RES / "group_yen.csv"); gs.round(1).to_csv(RES / "group_share.csv")

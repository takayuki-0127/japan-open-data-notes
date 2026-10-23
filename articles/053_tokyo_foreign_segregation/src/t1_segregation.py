"""T1：東京都の外国人は、国籍・地域によって住む場所がどれだけ違うか。
非類似度指数（D）を1979〜2026年の時系列と2026年の詳細表で計算し、立地係数で「どこに多いか」を見る"""
from common import *

x = load(); tot = load("0")
w = tot[tot.nat != "総数"].pivot_table(index="year", columns="nat", values="n")
w.to_csv(RES / "t1_tokyo_by_nat.csv", encoding="utf-8-sig")
# 時系列：国籍ごとの D（区市町村 53）
rows = []
for y in sorted(x.year.unique()):
    m = x[(x.year == y) & (x.nat != "総数")].pivot_table(index="area", columns="nat", values="n").fillna(0)
    m = m.drop(columns=["その他"], errors="ignore")
    D = dissimilarity(m); D.name = y; rows.append(D)
Dt = pd.DataFrame(rows); Dt.index.name = "year"; Dt.round(4).to_csv(RES / "t1_D_timeseries.csv", encoding="utf-8-sig")
# 2026年の詳細表（全国籍、人口1,000人以上）
d = detail2026(); big = d.sum()[d.sum() >= 1000].sort_values(ascending=False).index
D26 = dissimilarity(d)[big].sort_values()
pd.DataFrame({"D": D26, "n": d.sum()[D26.index]}).round(4).to_csv(RES / "t1_D_2026.csv", encoding="utf-8-sig"); print(D26.round(3))
# 立地係数（その区市町村の外国人に占める割合 ÷ 東京都全体の外国人に占める割合）
top = d.sum()[big].sort_values(ascending=False).index[:12]
lq = d[top].div(d.sum(axis=1), axis=0) / (d[top].sum() / d.values.sum())
areas = d.sum(axis=1).sort_values(ascending=False).index[:20]
lq.loc[areas].round(2).to_csv(RES / "t1_LQ_2026.csv", encoding="utf-8-sig")
# 各国籍で最も多い区市町村と、その集中度
conc = pd.DataFrame({"top_area": d[big].idxmax(), "top_share_pct": d[big].max() / d[big].sum() * 100, "n": d[big].sum()}).sort_values("n", ascending=False)
conc.round(1).to_csv(RES / "t1_top_area.csv", encoding="utf-8-sig"); print(conc.head(15).round(1))

s = {"total_1979": tot[(tot.nat == "総数") & (tot.year == 1979)].n.iloc[0], "total_2026": tot[(tot.nat == "総数") & (tot.year == 2026)].n.iloc[0],
     "total_2020": tot[(tot.nat == "総数") & (tot.year == 2020)].n.iloc[0], "total_2022": tot[(tot.nat == "総数") & (tot.year == 2022)].n.iloc[0],
     "D_korea_1979": Dt.loc[1979, "韓国・朝鮮"], "D_korea_2026": Dt.loc[2026, "韓国・朝鮮"], "D_china_1979": Dt.loc[1979, "中国・台湾"], "D_china_2026": Dt.loc[2026, "中国・台湾"],
     "D_vn_2010": Dt.loc[2010, "ベトナム"], "D_vn_2026": Dt.loc[2026, "ベトナム"], "D_us_2026": Dt.loc[2026, "米国"], "D_mm_2026": Dt.loc[2026, "ミャンマー"],
     "D26_max": D26.idxmax(), "D26_max_v": D26.max(), "D26_min": D26.idxmin(), "D26_min_v": D26.min(), "n_nat_2026_1000": len(big)}
pd.Series(s).to_csv(RES / "t1_summary.csv", header=["value"]); print(pd.Series(s))

fig, ax = plt.subplots(figsize=(10, 4.8))
cols = ["中国・台湾", "韓国・朝鮮", "ベトナム", "ネパール" if False else "ミャンマー", "フィリピン", "インド", "米国", "インドネシア"]
pal = [ORANGE, BLUE, GREEN, PURPLE, "#c4a000", "#d64f8a", INK, GRAY]
for c, col in zip(cols, pal): ax.plot(w.index, w[c] / 1e4, color=col, lw=2, label=c)
ax.set_ylabel("人数（万人、各年1月1日）"); ax.legend(frameon=False, ncol=4, fontsize=8.5, loc="upper left")
ax.set_title(f"東京都の外国人：{s['total_1979']/1e4:.0f}万人（1979年）→{s['total_2026']/1e4:.0f}万人（2026年）")
fig.text(0.01, -0.06, SOURCE + "\n（中国・台湾、韓国・朝鮮は2017年に分かれた区分を合算。ネパールなど表にない国籍は「その他」に含まれる）", fontsize=7, color="#8a8984")
fig.savefig(FIG / "t1_trend.png"); plt.close(fig)

fig, ax = plt.subplots(figsize=(8, 7))
o = D26.sort_values()
ax.barh(range(len(o)), o.values, color=[ORANGE if v > 0.5 else BLUE for v in o.values])
for i, (k, v) in enumerate(o.items()): ax.text(v + 0.01, i, f"{v:.2f}（{int(d[k].sum()):,}人）", va="center", fontsize=8)
ax.set_yticks(range(len(o))); ax.set_yticklabels(o.index, fontsize=9); ax.set_xlim(0, 1)
ax.set_xlabel("非類似度指数（0＝ほかの外国人と同じ分布、1＝まったく別の場所）")
ax.set_title("2026年：国籍・地域ごとの住む場所の偏り")
fig.text(0.01, -0.04, SOURCE + "\n（2026年1月1日、区市町村53、1,000人以上の国籍・地域。比べる相手はその国籍以外の外国人）", fontsize=7, color="#8a8984")
fig.savefig(FIG / "t1_D2026.png"); plt.close(fig)

fig, ax = plt.subplots(figsize=(10, 4.6))
for c, col in zip(["韓国・朝鮮", "中国・台湾", "ベトナム", "フィリピン", "米国", "ミャンマー", "インド"], [BLUE, ORANGE, GREEN, "#c4a000", INK, PURPLE, "#d64f8a"]):
    ax.plot(Dt.index, Dt[c], color=col, lw=2, label=c)
ax.set_ylabel("非類似度指数"); ax.legend(frameon=False, ncol=4, fontsize=8.5); ax.set_ylim(0, 0.8)
ax.set_title("住む場所の偏りの推移：多くの国籍で小さくなり、インドだけ強まった")
fig.text(0.01, -0.06, SOURCE + "\n（区市町村53。比べる相手はその国籍以外の外国人（「その他」を除く））", fontsize=7, color="#8a8984")
fig.savefig(FIG / "t1_D_trend.png"); plt.close(fig)

fig, ax = plt.subplots(figsize=(11, 6.5))
L = lq.loc[areas]
im = ax.imshow(np.log2(L.clip(lower=1 / 16)), cmap="RdBu_r", vmin=-3, vmax=3, aspect="auto")
ax.set_xticks(range(len(top))); ax.set_xticklabels(top, rotation=45, ha="right", fontsize=9); ax.set_yticks(range(len(areas))); ax.set_yticklabels(areas, fontsize=9)
for i in range(L.shape[0]):
    for j in range(L.shape[1]):
        v = L.iloc[i, j]; ax.text(j, i, f"{v:.1f}", ha="center", va="center", fontsize=7, color="white" if abs(np.log2(max(v, 1 / 16))) > 1.8 else INK)
cb = fig.colorbar(im, ax=ax, shrink=0.7); cb.set_label("立地係数（log2）")
ax.set_title("立地係数：その区市町村にどれだけ多いか（1＝東京都全体と同じ割合）")
fig.text(0.01, -0.04, SOURCE + "\n（2026年1月1日。外国人が多い20区市×人数の多い12国籍・地域。立地係数＝区市の外国人に占める割合÷都全体の外国人に占める割合）", fontsize=7, color="#8a8984")
fig.savefig(FIG / "t1_LQ.png"); plt.close(fig)

"""日照時間の「晴れの県ランキング」は、何年で入れ替わるか（気象台など47地点、1987〜2025年）"""
from common import *

d, w = load()
rk = w.rank(axis=1, ascending=False)  # 1 = 日照時間が最も長い
rk.to_csv(RES / "a198_rank_by_year.csv", encoding="utf-8")
L = [f"期間 {Y0}〜{Y1}年（{len(w)}年）、47地点。資料不足値 {int(w.isna().sum().sum())}個は除外"]
blocks = {"1987-1999": (1987, 1999), "2000-2012": (2000, 2012), "2013-2025": (2013, 2025)}
bm = pd.DataFrame({k: w.loc[a:b].mean() for k, (a, b) in blocks.items()})
br = bm.rank(ascending=False)
out = bm.round(1).join(br.add_suffix("_rank"))
out.to_csv(RES / "a198_block_means.csv", encoding="utf-8")
for k in blocks:
    s = bm[k].sort_values(ascending=False)
    L.append(f"{k} 平均 上位5: " + "、".join(f"{p} {v:.0f}" for p, v in s.head(5).items()) + " / 下位5: " + "、".join(f"{p} {v:.0f}" for p, v in s.tail(5).items()))
sp = lambda a, b: pd.Series(a).corr(pd.Series(b), method="spearman")
L.append(f"期間平均の順位相関: 1987-99 と 2000-12 {sp(bm.iloc[:,0], bm.iloc[:,1]):.2f}、2000-12 と 2013-25 {sp(bm.iloc[:,1], bm.iloc[:,2]):.2f}、1987-99 と 2013-25 {sp(bm.iloc[:,0], bm.iloc[:,2]):.2f}")
ch = (br.iloc[:, 0] - br.iloc[:, 2]).sort_values()
L.append("1987-99→2013-25 順位が上がった: " + "、".join(f"{p} {int(br.iloc[:,0][p])}→{int(br.iloc[:,2][p])}位" for p in ch.index[::-1][:5]) + " / 下がった: " + "、".join(f"{p} {int(br.iloc[:,0][p])}→{int(br.iloc[:,2][p])}位" for p in ch.index[:5]))
# ラグ別の順位相関（年ごとの値どうし）
lag = {}
for k in range(1, 31):
    lag[k] = np.nanmean([sp(w.loc[y], w.loc[y + k]) for y in w.index if y + k in w.index])
lag = pd.Series(lag); lag.to_csv(RES / "a198_lag_corr.csv", header=["spearman"], encoding="utf-8")
L.append("隣の年どうしの順位相関 平均 " + f"{lag[1]:.2f}（最小 {min(sp(w.loc[y], w.loc[y+1]) for y in w.index[:-1]):.2f}）、5年差 {lag[5]:.2f}、10年差 {lag[10]:.2f}、20年差 {lag[20]:.2f}、30年差 {lag[30]:.2f}")
# 1位・上位5の回数
top1 = rk.idxmin(axis=1).value_counts()
top5 = (rk <= 5).sum().sort_values(ascending=False)
bot5 = (rk >= 43).sum().sort_values(ascending=False)
L.append("年ごとの1位の回数: " + "、".join(f"{p} {n}回" for p, n in top1.items()))
L.append("上位5に入った回数: " + "、".join(f"{p} {n}" for p, n in top5[top5 > 0].items()))
L.append("下位5に入った回数: " + "、".join(f"{p} {n}" for p, n in bot5[bot5 > 0].items()))
sd = rk.std().sort_values()
L.append("順位の動き（標準偏差）小さい: " + "、".join(f"{p} {v:.1f}" for p, v in sd.head(5).items()) + " / 大きい: " + "、".join(f"{p} {v:.1f}" for p, v in sd.tail(5).items()))
nat = w.mean(axis=1)
L.append(f"47地点平均 1987-99 {nat.loc[1987:1999].mean():.0f}h → 2013-25 {nat.loc[2013:2025].mean():.0f}h、最長年 {nat.idxmax()} {nat.max():.0f}h、最短年 {nat.idxmin()} {nat.min():.0f}h")
(RES / "a198_summary.txt").write_text("\n".join(L), encoding="utf-8")
print("\n".join(L))

# 図1：期間ごとの順位（上位と下位の入れ替わり）
fig, ax = plt.subplots(figsize=(9, 10.5))
xs = [0, 1, 2]
order = br.iloc[:, 2].sort_values().index
for p in order:
    r = br.loc[p].values
    hl = (r.min() <= 5) or (r.max() >= 43)
    big = abs(r[0] - r[2]) >= 12
    c = BLUE if r[2] <= 10 else (ORANGE if r[2] >= 38 else (PURPLE if big else LIGHT))
    ax.plot(xs, r, color=c, lw=1.8 if (hl or big) else 0.8, marker="o", ms=3, alpha=1 if (hl or big) else 0.6)
    ax.text(2.06, r[2], f"{p}", va="center", fontsize=7.5, color=c if c != LIGHT else GRAY)
    if hl or big:
        ax.text(-0.06, r[0], p, va="center", ha="right", fontsize=7.5, color=c if c != LIGHT else GRAY)
ax.set_ylim(48, 0); ax.set_xlim(-0.35, 2.35)
ax.set_xticks(xs); ax.set_xticklabels(["1987〜1999年\n平均", "2000〜2012年\n平均", "2013〜2025年\n平均"])
ax.set_yticks([1, 5, 10, 20, 30, 40, 47]); ax.set_ylabel("年間日照時間の順位（1位が最も長い）")
ax.spines["bottom"].set_visible(False)
ax.set_title("年間日照時間の順位（47地点、13年ずつの平均）")
save(fig, "a198_rank_blocks.png")

# 図2：何年離れると順位が入れ替わるか
fig, ax = plt.subplots(figsize=(9, 4.5))
ax.plot(lag.index, lag.values, color=BLUE, marker="o", ms=4)
ax.axhline(sp(bm.iloc[:, 0], bm.iloc[:, 2]), color=ORANGE, ls="--", lw=1)
ax.text(30, sp(bm.iloc[:, 0], bm.iloc[:, 2]) + 0.015, "13年平均どうし（1987-99と2013-25）", ha="right", color=ORANGE, fontsize=9)
for k in [1, 10, 20, 30]:
    ax.annotate(f"{lag[k]:.2f}", (k, lag[k]), xytext=(0, 8), textcoords="offset points", ha="center", fontsize=9)
ax.set_ylim(0.4, 1); ax.set_xlabel("比べる2つの年の間隔（年）"); ax.set_ylabel("順位相関（スピアマン）の平均")
ax.set_title("年ごとの日照時間の順位は、何年離れるとどれだけ変わるか")
save(fig, "a198_lag.png")

# 図3：上位5・下位5に入った回数
t = top5[top5 > 0]; b = bot5[bot5 > 0]
fig, axes = plt.subplots(1, 2, figsize=(10, 5.5))
for ax, s, c, tt in [(axes[0], t, BLUE, "上位5位に入った年の数"), (axes[1], b, ORANGE, "下位5位に入った年の数")]:
    s = s.sort_values()
    ax.barh(range(len(s)), s.values, color=c, height=0.7)
    ax.set_yticks(range(len(s))); ax.set_yticklabels(s.index, fontsize=8.5)
    for i, v in enumerate(s.values):
        ax.text(v + 0.3, i, str(v), va="center", fontsize=8)
    ax.set_title(tt, fontsize=11); ax.set_xlabel(f"年（{Y0}〜{Y1}年の{len(w)}年中）")
fig.suptitle("日照時間の上位と下位に入った県（年ごと）", y=1.02)
save(fig, "a198_top_bottom.png")

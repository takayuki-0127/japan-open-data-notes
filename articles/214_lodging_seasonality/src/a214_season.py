"""A214 季節パターンで都道府県を分ける：延べ宿泊者数の月別季節指数を階層クラスタリング（Ward法）"""
import numpy as np, pandas as pd, matplotlib.pyplot as plt
from scipy.cluster.hierarchy import linkage, fcluster
from common import load, profile, TILE, FIG, RES, SOURCE, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, PURPLE

d = load()
P25, P19 = profile(d, 2025), profile(d, 2019)
K = 5
Z = linkage(P25.values, "ward"); lab = fcluster(Z, K, "maxclust")
cl = pd.Series(lab, index=P25.index)
# クラスタを特徴で名づける：ピーク月で並べる
cent = P25.groupby(cl).mean()
peakm = cent.idxmax(axis=1); amp = cent.max(axis=1) - cent.min(axis=1)
order = amp.sort_values(ascending=False).index.tolist()
REP = {"東京都": "1年を通して差が小さい", "京都府": "夏と秋に山、冬が少ない", "北海道": "冬にも山（4月が底）", "青森県": "8月と10月に集中", "山梨県": "7〜8月に強く集中"}
names = {cl[p]: n for p, n in REP.items()}
assert len(set(names)) == K
cl_name = cl.map(names)
strength = (P25.max(axis=1) - P25.min(axis=1)).rename("range")
cv = (P25.std(axis=1) / 100 * 100).rename("cv_pct")
corr = pd.Series({p: np.corrcoef(P25.loc[p], P19.loc[p])[0, 1] for p in P25.index}, name="corr_2019_2025")
lab19 = fcluster(linkage(P19.values, "ward"), K, "maxclust")
from sklearn.metrics import adjusted_rand_score
ari = adjusted_rand_score(lab, lab19)
tot = d[d.year == 2025].groupby("pref")[["total", "foreign", "tour50"]].sum()
fshare = (tot.foreign / tot.total * 100).rename("foreign_share")
tshare = (tot.tour50 / tot.total * 100).rename("tour50_share")
res = pd.concat([cl.rename("cluster"), cl_name.rename("cluster_name"), strength, cv, P25.idxmax(axis=1).rename("peak_month"), P25.max(axis=1).rename("peak_index"), P25.idxmin(axis=1).rename("low_month"), corr, fshare, tshare], axis=1)
res.round(3).to_csv(RES / "pref_season_clusters_2025.csv"); P25.round(1).to_csv(RES / "season_index_2025.csv"); P19.round(1).to_csv(RES / "season_index_2019.csv"); cent.round(1).to_csv(RES / "cluster_centroids_2025.csv")

L = []
nat = d[d.year == 2025].groupby("month").total.sum().div(np.array([31,28,31,30,31,30,31,31,30,31,30,31])); nat = nat / nat.mean() * 100
L.append("全国の季節指数（2025）: " + ", ".join(f"{m}月 {v:.0f}" for m, v in nat.items()))
for c in order:
    m = res[res.cluster == c].sort_values("range", ascending=False)
    L.append(f"[{names[c]}] {len(m)}県: " + "、".join(m.index) + f" ／ 平均の振れ幅 {m['range'].mean():.0f}、外国人比率の平均 {m.foreign_share.mean():.1f}%、観光目的50%以上施設の割合 {m.tour50_share.mean():.0f}%")
L.append("季節の振れ幅（最大月−最小月の指数差）上位: " + ", ".join(f"{p} {v:.0f}（{res.loc[p,'peak_month']}月 {res.loc[p,'peak_index']:.0f}）" for p, v in strength.sort_values(ascending=False).head(6).items()))
L.append("下位: " + ", ".join(f"{p} {v:.0f}" for p, v in strength.sort_values().head(6).items()))
L.append(f"2019年と2025年の季節指数の相関：中央値 {corr.median():.3f}、最小 {corr.idxmin()} {corr.min():.3f}。2019年のクラスタとの一致度（ARI） {ari:.2f}")
L.append(f"振れ幅と観光目的施設の割合の相関 {np.corrcoef(strength, tshare)[0,1]:.2f}、外国人比率との相関 {np.corrcoef(strength, fshare)[0,1]:.2f}")
open(RES / "summary.txt", "w").write("\n".join(L) + "\n"); print("\n".join(L))

pal = [ORANGE, BLUE, GREEN, PURPLE, GRAY, "#c4471d"]
colc = {c: pal[i] for i, c in enumerate(order)}
fig, axes = plt.subplots(1, K, figsize=(12, 3.6), sharey=True)
for ax, c in zip(axes, order):
    for p in cl.index[cl == c]:
        ax.plot(range(1, 13), P25.loc[p], color=colc[c], alpha=0.25, lw=1)
    ax.plot(range(1, 13), cent.loc[c], color=colc[c], lw=2.6)
    ax.axhline(100, color=GRAY, lw=0.6)
    ax.set_title(f"{names[c]}\n{(cl==c).sum()}都道府県", fontsize=10)
    ax.set_xticks([1, 4, 7, 10]); ax.set_xticklabels(["1月", "4月", "7月", "10月"])
axes[0].set_ylabel("季節指数（年平均＝100）")
fig.suptitle("延べ宿泊者数の季節パターン（2025年、1日当たり）", y=1.03)
fig.text(0.01, -0.04, SOURCE + "。Ward法で5つに分類", fontsize=8, color=GRAY); fig.savefig(FIG / "a214_clusters.png"); plt.close()

fig, ax = plt.subplots(figsize=(8, 6.5))
for p, (x, y) in TILE.items():
    c = colc[cl[p]]
    ax.add_patch(plt.Rectangle((x, -y), 0.92, 0.92, color=c, alpha=0.85))
    ax.text(x + 0.46, -y + 0.55, p.replace("県", "").replace("府", "").replace("都", "") if p != "北海道" else "北海道", ha="center", va="center", fontsize=8.5, color="white")
    ax.text(x + 0.46, -y + 0.22, f"{res.loc[p,'peak_month']}月", ha="center", va="center", fontsize=7, color="white")
for i, c in enumerate(order):
    ax.add_patch(plt.Rectangle((4.2, -8.6 - i * 0.55), 0.4, 0.4, color=colc[c])); ax.text(4.8, -8.4 - i * 0.55, names[c], va="center", fontsize=9)
ax.set_xlim(-0.2, 13.2); ax.set_ylim(-11.3, 1.1); ax.axis("off"); ax.set_aspect("equal")
ax.set_title("季節パターンのグループ（タイル内の数字はピークの月）")
fig.text(0.01, 0.0, SOURCE, fontsize=8, color=GRAY); fig.savefig(FIG / "a214_tilemap.png"); plt.close()

ordp = res.sort_values(["cluster", "range"], key=lambda x: x.map({c: i for i, c in enumerate(order)}) if x.name == "cluster" else -x).index
fig, ax = plt.subplots(figsize=(8, 10))
im = ax.imshow(P25.loc[ordp].values, cmap="RdBu_r", vmin=40, vmax=160, aspect="auto")
ax.set_yticks(range(len(ordp))); ax.set_yticklabels(ordp, fontsize=7.5)
ax.set_xticks(range(12)); ax.set_xticklabels([f"{m}月" for m in range(1, 13)], fontsize=9)
b = 0
for c in order:
    n = (cl == c).sum(); b += n
    if b < len(ordp): ax.axhline(b - 0.5, color=INK, lw=1)
    ax.text(12.2, b - n / 2 - 0.5, names[c], va="center", fontsize=9, color=colc[c])
cb = fig.colorbar(im, ax=ax, shrink=0.4, pad=0.28); cb.set_label("季節指数（年平均＝100）")
ax.set_title("都道府県別の季節指数（2025年、グループ順）")
fig.text(0.01, 0.06, SOURCE, fontsize=8, color=GRAY); fig.savefig(FIG / "a214_heatmap.png"); plt.close()

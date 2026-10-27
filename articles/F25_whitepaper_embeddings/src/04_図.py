"""04 図：5枚＋頑健性1枚"""
import json
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from common import RES, FIG, BLUE, ORANGE, RED, GRAY

themes = pd.read_csv(RES / "themes.csv")
labels = json.load(open(RES / "theme_labels.json", encoding="utf-8"))  # 手で付けた短い名前（04 の前に作る）
lab = {int(k): v for k, v in labels.items()}
order = themes.sort_values("mean_year").theme.tolist()
cmap = plt.get_cmap("tab20")
pal = [cmap(i) for i in list(range(0, 20, 2)) + [1, 5]]
col = {t: pal[i] for i, t in enumerate(order)}

# 1 UMAP
u = pd.read_csv(RES / "umap_2d.csv")
fig, axes = plt.subplots(1, 2, figsize=(12.5, 5.6))
ax = axes[0]
xl = u.x.quantile([0.005, 0.995]).values; yl = u.y.quantile([0.005, 0.995]).values
pos = {}
for t in order:
    s = u[u.theme == t]
    ax.scatter(s.x, s.y, s=2.5, color=col[t], alpha=0.6, lw=0)
    pos[t] = [s.x.median(), s.y.median()]
dy = (yl[1] - yl[0]) * 0.045
for _ in range(60):  # 重なったラベルを上下にずらす
    moved = False
    ts = sorted(pos, key=lambda t: pos[t][1])
    for i, a in enumerate(ts):
        for b in ts[i + 1:]:
            if abs(pos[a][0] - pos[b][0]) < (xl[1] - xl[0]) * 0.16 and abs(pos[a][1] - pos[b][1]) < dy:
                pos[a][1] -= dy * 0.3; pos[b][1] += dy * 0.3; moved = True
    if not moved:
        break
for t in order:
    ax.text(pos[t][0], pos[t][1], lab[t], fontsize=8.5, ha="center", va="center",
            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec=col[t], lw=1.0, alpha=0.9))
ax.set_xlim(*xl); ax.set_ylim(*yl)
ax.set_title("テーマ（KMeans・12）で色分け"); ax.set_xticks([]); ax.set_yticks([])
ax = axes[1]
sc = ax.scatter(u.x, u.y, s=2.5, c=u.year, cmap="viridis", alpha=0.6, lw=0)
ax.set_xlim(*xl); ax.set_ylim(*yl)
cb = fig.colorbar(sc, ax=ax, fraction=0.04, pad=0.01); cb.set_label("白書の年度")
ax.set_title("白書の年度で色分け"); ax.set_xticks([]); ax.set_yticks([])
fig.suptitle("経済白書・経済財政白書の約500字の塊を、文埋め込み（ruri-v3）→UMAP で2次元にした地図", fontsize=11.5)
fig.savefig(FIG / "f25_umap.png"); plt.close(fig)

# 2 テーマ構成比の推移
sh = pd.read_csv(RES / "theme_share_by_year.csv", index_col=0)
sh.columns = sh.columns.astype(int)
sh = sh[order]
fig, ax = plt.subplots(figsize=(12, 5.6))
ax.stackplot(sh.index, sh.T.values, colors=[col[t] for t in order], alpha=0.9, labels=[lab[t] for t in order])
ax.set_xlim(sh.index.min(), sh.index.max()); ax.set_ylim(0, 100)
ax.set_ylabel("その年の白書の中の割合（%）")
ax.legend(loc="upper left", bbox_to_anchor=(1.0, 1.0), fontsize=8.8, frameon=False, reverse=True)
ax.set_title("テーマの構成比の推移（年度ごとのチャンクの割合）")
fig.savefig(FIG / "f25_theme_share.png"); plt.close(fig)

# 3 年どうしの近さ
S = pd.read_csv(RES / "year_similarity.csv", index_col=0)
fig, axes = plt.subplots(1, 2, figsize=(12.5, 5.4), gridspec_kw=dict(width_ratios=[1.15, 1]))
ax = axes[0]
im = ax.imshow(S.values, cmap="magma", vmin=np.quantile(S.values, 0.02), vmax=1)
yrs = S.index.astype(int)
tick = [i for i, y in enumerate(yrs) if y % 5 == 0]
ax.set_xticks(tick); ax.set_xticklabels(yrs[tick], rotation=90); ax.set_yticks(tick); ax.set_yticklabels(yrs[tick])
fig.colorbar(im, ax=ax, fraction=0.045, pad=0.02)
ax.set_title("年度どうしの内容の近さ（年の平均ベクトル、全体の平均を引く）", fontsize=10.5)
ax = axes[1]
p = pd.read_csv(RES / "year_sim_prev.csv")
ax.plot(p.year, p.sim_prev, color=BLUE, marker="o", ms=3)
low = p.nsmallest(4, "sim_prev").sort_values("year")
for k, r in enumerate(low.itertuples()):
    ax.annotate(str(r.year), (r.year, r.sim_prev), xytext=(-10 if k % 2 == 0 else 10, -13), textcoords="offset points", ha="center", fontsize=8.5, color=RED)
for a, b in [(1986, 1999), (2000, 2014), (2015, 2025)]:
    m = p[(p.year >= a) & (p.year <= b)].sim_prev.mean()
    ax.hlines(m, a, b, color=ORANGE, lw=2, alpha=0.8)
    ax.text((a + b) / 2, m + 0.035, f"平均 {m:.2f}", ha="center", fontsize=9, color=ORANGE)
pass
ax.set_title("前の年度との近さ（低いほど話題が入れ替わった）"); ax.set_xlabel("年度")
fig.savefig(FIG / "f25_year_similarity.png"); plt.close(fig)

# 4 語の検索の推移
q = pd.read_csv(RES / "query_share_by_year.csv")
qs = ["物価", "デフレ", "賃金", "不良債権", "財政赤字", "少子化・人口減少", "デジタル・AI", "環境・脱炭素"]
fig, axes = plt.subplots(2, 4, figsize=(13, 5.8), sharex=True)
for ax, name in zip(axes.flat, qs):
    g = q[q["query"] == name]
    ax.bar(g.year, g.share, color=BLUE, width=0.85)
    pk = g.loc[g.share.idxmax()]
    ax.set_title(f"{name}（最多 {int(pk.year)}年度）", fontsize=10)
    ax.axhline(1, color=GRAY, lw=0.7, ls="--")
for ax in axes[:, 0]:
    ax.set_ylabel("近いチャンクの割合（%）")
fig.suptitle("質問文に近いチャンク（全体の上位1%の近さ）が、その年度の白書の何%か（破線は平均の1%）", fontsize=11)
fig.tight_layout()
fig.savefig(FIG / "f25_query_trend.png"); plt.close(fig)

# 5 検索デモ（見出しだけ）
d = pd.read_csv(RES / "search_demo.csv")
show = ["不良債権", "少子化・人口減少", "デジタル・AI"]
fig, ax = plt.subplots(figsize=(12, 5.2)); ax.axis("off")
y = 0.97
for name in show:
    ax.text(0.0, y, f"質問：「{name}」に近い節（上位5）", fontsize=11, fontweight="bold", color=BLUE, transform=ax.transAxes)
    y -= 0.06
    for r in d[d["query"] == name].itertuples():
        h = r.heading if len(r.heading) <= 46 else r.heading[:46] + "…"
        ax.text(0.02, y, f"{r.rank}. {r.year}年度　{h}", fontsize=9.8, transform=ax.transAxes)
        ax.text(0.98, y, f"近さ {r.sim:.3f}", fontsize=9, color=GRAY, ha="right", transform=ax.transAxes)
        y -= 0.052
    y -= 0.02
ax.set_title("検索デモ：質問文を埋め込みにして、近い本文の塊を探す（表示は節の見出しだけ）", fontsize=11)
fig.savefig(FIG / "f25_search_demo.png"); plt.close(fig)

# 6 頑健性
rc = pd.read_csv(RES / "robust_clusters.csv")
rq = pd.read_csv(RES / "robust_queries.csv")
fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.8), gridspec_kw=dict(width_ratios=[1, 1.1]))
ax = axes[0]
r2 = rc[rc.setting != rc.setting.iloc[0]]
ax.barh(range(len(r2)), r2.ari, color=[ORANGE if "単語" in s else BLUE for s in r2.setting])
ax.set_yticks(range(len(r2))); ax.set_yticklabels(r2.setting, fontsize=9); ax.invert_yaxis()
for i, v in enumerate(r2.ari):
    ax.text(v + 0.01, i, f"{v:.2f}", va="center", fontsize=8.5)
ax.set_xlim(0, 1); ax.set_xlabel("基本のテーマ分けとの一致（ARI）")
ax.set_title("テーマ分けは設定でどれだけ変わるか")
ax = axes[1]
pv = rq.pivot(index="query", columns="length", values="corr")
im = ax.imshow(pv.values, cmap="Blues", vmin=0, vmax=1)
ax.set_xticks(range(pv.shape[1])); ax.set_xticklabels([("チャンク1,000字" if str(c).isdigit() else "近さの閾値 " + c) for c in pv.columns], fontsize=8.5, rotation=25, ha="right")
ax.set_yticks(range(pv.shape[0])); ax.set_yticklabels(pv.index, fontsize=9)
for i in range(pv.shape[0]):
    for j in range(pv.shape[1]):
        ax.text(j, i, f"{pv.values[i, j]:.2f}", ha="center", va="center", fontsize=8.5, color="white" if pv.values[i, j] > 0.6 else "#222")
ax.set_title("語の検索の推移は変わるか（基本との相関）")
fig.tight_layout()
fig.savefig(FIG / "f25_robustness.png"); plt.close(fig)
print("figures ok")

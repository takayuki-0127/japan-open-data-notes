"""F39 図"""
import json
import numpy as np
import pandas as pd
from common import DATA, RES, FIG, LABELS, MAIN_VARS, setup_font

plt = setup_font()
FIG.mkdir(exist_ok=True)
names = MAIN_VARS
lab = [LABELS[v] for v in names]
meta = json.load(open(RES / "meta.json"))
TH_B0, TH_LAG = meta["th_B0"], meta["th_lag"]

# 円の上に6変数を置く
ang = np.linspace(90, 90 - 360, len(names), endpoint=False) * np.pi / 180
POS = {v: (np.cos(a), np.sin(a)) for v, a in zip(names, ang)}


def draw_graph(ax, edges, title, undirected=()):
    """edges: (cause, effect, weight, style)"""
    for v, (x, y) in POS.items():
        ax.add_patch(plt.Circle((x, y), 0.26, color="#eef2f7", ec="#33415c", lw=1.2, zorder=3))
        ax.text(x, y, LABELS[v].replace("（", "\n（"), ha="center", va="center", fontsize=8, zorder=4)
    for a, b in undirected:
        (x1, y1), (x2, y2) = POS[a], POS[b]
        ax.plot([x1, x2], [y1, y2], color="#999999", lw=1.5, ls="--", zorder=1)
    for c, e, w, col in edges:
        (x1, y1), (x2, y2) = POS[c], POS[e]
        dx, dy = x2 - x1, y2 - y1
        L = np.hypot(dx, dy)
        sx, sy = x1 + dx / L * 0.28, y1 + dy / L * 0.28
        ex, ey = x2 - dx / L * 0.30, y2 - dy / L * 0.30
        ax.annotate("", xy=(ex, ey), xytext=(sx, sy),
                    arrowprops=dict(arrowstyle="-|>", color=col, lw=0.8 + 3 * min(abs(w), 1),
                                    connectionstyle="arc3,rad=0.12", shrinkA=0, shrinkB=0), zorder=2)
    ax.set_xlim(-1.45, 1.45); ax.set_ylim(-1.45, 1.45); ax.set_aspect("equal"); ax.axis("off")
    ax.set_title(title, fontsize=10)


B0 = pd.read_csv(RES / "lingam_B0_main.csv", index_col=0).values
BL = pd.read_csv(RES / "lingam_Blag_main.csv", index_col=0).values
gr = pd.read_csv(RES / "granger_main.csv")
pce = pd.read_csv(RES / "pc_main_edges.csv")

# ---- 図1 手法別の因果グラフ ----
fig, axes = plt.subplots(1, 3, figsize=(13, 4.8))
e1 = [(names[j], names[i], B0[i, j], "#c0392b") for i in range(6) for j in range(6) if i != j and abs(B0[i, j]) > TH_B0]
e1 += [(names[j], names[i], BL[i, j], "#2e6da4") for i in range(6) for j in range(6) if i != j and abs(BL[i, j]) > TH_LAG]
draw_graph(axes[0], e1, "VAR-LiNGAM\n赤＝同じ月、青＝時間差（係数の合計）")
g = gr[gr.p < 0.05 / len(gr)]
draw_graph(axes[1], [(r.cause, r.effect, 0.5, "#2e6da4") for r in g.itertuples()],
           f"グレンジャー因果\n（p<0.05 を {len(gr)} 回の検定で Bonferroni 補正）")
d = pce[pce.type == "→"]; u = pce[pce.type == "—"]
draw_graph(axes[2], [(r.cause, r.effect, 0.5, "#c0392b") for r in d.itertuples()],
           "PC アルゴリズム（同じ月、VAR の残差）\n破線＝向きが決まらない線", undirected=[(r.cause, r.effect) for r in u.itertuples()])
fig.suptitle("同じデータでも、手法によって出てくる矢印が違う（前年比、1995年1月〜2026年8月）", fontsize=12, y=0.99)
fig.subplots_adjust(top=0.80, wspace=0.05, left=0.02, right=0.98, bottom=0.02); fig.savefig(FIG / "f39_graphs_by_method.png", dpi=150); plt.close(fig)

# ---- 図2 ブートストラップで矢印が出た割合 ----
bb0 = pd.read_csv(RES / "lingam_boot_B0.csv", index_col=0)
bbl = pd.read_csv(RES / "lingam_boot_Blag.csv", index_col=0)
pcb = pd.read_csv(RES / "pc_boot_dir.csv", index_col=0)  # 行=原因
fig, axes = plt.subplots(1, 3, figsize=(15, 5.2))
for k, (ax, M, t) in enumerate([(axes[0], bb0.values, "VAR-LiNGAM 同じ月"), (axes[1], bbl.values, "VAR-LiNGAM 時間差"),
                 (axes[2], pcb.values.T, "PC（向きつき）")]):
    M = M.copy(); np.fill_diagonal(M, np.nan)
    im = ax.imshow(M, vmin=0, vmax=1, cmap="Blues")
    ax.set_xticks(range(6)); ax.set_xticklabels(lab, rotation=45, ha="right", fontsize=8)
    ax.set_yticks(range(6)); ax.set_yticklabels(lab if k == 0 else [], fontsize=8)
    ax.set_xlabel("原因"); ax.set_ylabel("結果" if k == 0 else "")
    for i in range(6):
        for j in range(6):
            if i != j:
                ax.text(j, i, f"{M[i, j]*100:.0f}", ha="center", va="center", fontsize=8,
                        color="white" if M[i, j] > 0.6 else "black")
    ax.set_title(t, fontsize=10)
fig.colorbar(im, ax=axes, fraction=0.02, label="200回のうち矢印が出た割合")
fig.suptitle("ブートストラップ200回で、同じ矢印が何%出たか（数字は%）", fontsize=12)
fig.savefig(FIG / "f39_bootstrap.png", dpi=150, bbox_inches="tight"); plt.close(fig)

# ---- 図3 期間で分けた場合 ----
per = json.load(open(RES / "period_graphs.json"))
keys = list(per.keys())[1:4]
fig, axes = plt.subplots(1, 3, figsize=(13, 4.8))
for ax, k in zip(axes, keys):
    b0 = np.array(per[k]["B0"]); bl = np.array(per[k]["Blag"])
    e = [(names[j], names[i], b0[i, j], "#c0392b") for i in range(6) for j in range(6) if i != j and abs(b0[i, j]) > TH_B0]
    e += [(names[j], names[i], bl[i, j], "#2e6da4") for i in range(6) for j in range(6) if i != j and abs(bl[i, j]) > TH_LAG]
    draw_graph(ax, e, k)
fig.suptitle("期間を分けると、VAR-LiNGAM の矢印は入れ替わる（赤＝同じ月、青＝時間差）", fontsize=12, y=0.99)
fig.subplots_adjust(top=0.84, wspace=0.05, left=0.02, right=0.98, bottom=0.02); fig.savefig(FIG / "f39_periods.png", dpi=150); plt.close(fig)

# ---- 図4 グレンジャー因果の p 値の表 ----
P = gr.pivot(index="effect", columns="cause", values="p").reindex(index=names, columns=names)
fig, ax = plt.subplots(figsize=(7.2, 5.6))
M = -np.log10(P.values.astype(float))
im = ax.imshow(M, cmap="Oranges", vmin=0, vmax=6)
for i in range(6):
    for j in range(6):
        if i != j:
            p = P.values[i, j]
            s = "<0.001" if p < 0.001 else f"{p:.3f}"
            ax.text(j, i, s, ha="center", va="center", fontsize=8, color="white" if M[i, j] > 4 else "black")
ax.set_xticks(range(6)); ax.set_xticklabels(lab, rotation=45, ha="right", fontsize=8)
ax.set_yticks(range(6)); ax.set_yticklabels(lab, fontsize=8)
ax.set_xlabel("原因（過去の値）"); ax.set_ylabel("結果")
ax.set_title(f"グレンジャー因果の p 値（VAR、ラグ {meta['lags_main']}）\n色が濃いほど「過去の値が予測に効く」", fontsize=10)
fig.colorbar(im, ax=ax, label="−log10(p)")
fig.tight_layout(); fig.savefig(FIG / "f39_granger.png", dpi=150); plt.close(fig)

# ---- 図5 前提（非ガウス性）の確認 ----
nm = pd.read_csv(RES / "normality.csv")
yoy = pd.read_csv(DATA / "yoy.csv", index_col=0, parse_dates=True)
from statsmodels.tsa.api import VAR
X = (yoy[names] - yoy[names].mean()) / yoy[names].std()
R = VAR(X).fit(meta["lags_main"]).resid
fig, axes = plt.subplots(2, 3, figsize=(12, 6.4))
for ax, v in zip(axes.ravel(), names):
    e = R[v].values; e = (e - e.mean()) / e.std()
    ax.hist(e, bins=40, density=True, color="#7f9cc3", alpha=0.85)
    xs = np.linspace(-5, 5, 200); ax.plot(xs, np.exp(-xs**2 / 2) / np.sqrt(2 * np.pi), color="#c0392b", lw=1.2)
    r = nm[nm["var"] == v].iloc[0]
    ax.set_title(f"{LABELS[v]}\n尖度 {r['excess_kurtosis']:+.1f}・歪度 {r['skew']:+.2f}・JB p={r['jb_p']:.1e}", fontsize=9)
    ax.set_xlim(-5, 5)
fig.suptitle("LiNGAM の前提：VAR の残差が正規分布（赤線）から外れているか", fontsize=12)
fig.tight_layout(); fig.savefig(FIG / "f39_nongaussian.png", dpi=150); plt.close(fig)

# ---- 図6 頑健性：主な矢印が設定でどう変わるか ----
rob = pd.read_csv(RES / "robustness.csv")
rob["edge"] = rob["cause"].map(LABELS) + "→" + rob["effect"].map(LABELS)
show = [("imp", "cpi"), ("cpi", "imp"), ("imp", "wage"), ("fx", "cpi"), ("cpi", "wage"), ("wage", "cpi"), ("unemp", "wage"), ("fx", "imp")]
sets = list(dict.fromkeys(rob["setting"]))
fig, axes = plt.subplots(1, 2, figsize=(14, 5.4), sharey=True)
for ax, col, th, t in [(axes[0], "lingam_B0", TH_B0, "VAR-LiNGAM 同じ月の係数"), (axes[1], "lingam_lag", TH_LAG, "VAR-LiNGAM 時間差の係数の合計")]:
    M = np.full((len(show), len(sets)), np.nan)
    for i, (c, e) in enumerate(show):
        for j, s in enumerate(sets):
            r = rob[(rob.cause == c) & (rob.effect == e) & (rob.setting == s)]
            if len(r):
                M[i, j] = r[col].iloc[0]
    im = ax.imshow(M, cmap="RdBu_r", vmin=-0.6, vmax=0.6, aspect="auto")
    for i in range(len(show)):
        for j in range(len(sets)):
            if not np.isnan(M[i, j]):
                ax.text(j, i, f"{M[i, j]:.2f}" if abs(M[i, j]) > 0.005 else "0", ha="center", va="center", fontsize=7)
    ax.set_xticks(range(len(sets))); ax.set_xticklabels([s.replace("（", "\n（") for s in sets], rotation=60, ha="right", fontsize=7)
    ax.set_yticks(range(len(show))); ax.set_yticklabels([f"{LABELS[c]}→{LABELS[e]}" for c, e in show], fontsize=8)
    ax.set_title(t, fontsize=10)
fig.colorbar(im, ax=axes, fraction=0.02, label="標準化した係数（0＝矢印なし）")
fig.suptitle("設定を変えたときの主な矢印（空欄は変数を外した設定）", fontsize=12)
fig.savefig(FIG / "f39_robustness.png", dpi=150, bbox_inches="tight"); plt.close(fig)
print("figures done")

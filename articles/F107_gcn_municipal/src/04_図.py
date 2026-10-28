"""04 図：結果の5枚の図と、残差の空間的な偏り（Moran's I）"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from libpysal.weights import W
from esda.moran import Moran
from common import DATA, RES, FIG, SEED

S = pd.read_csv(RES / "summary.csv")
F = pd.read_csv(RES / "folds.csv")
P = pd.read_csv(RES / "predictions_main.csv", dtype={"code": str})
nodes = pd.read_csv(DATA / "nodes.csv", dtype={"code": str})
NAME = {"ridge": "線形回帰", "lgbm": "LightGBM", "lgbm_nx": "LightGBM\n＋隣の指標", "lgbm_ny": "LightGBM\n＋隣の指標\n＋隣の出生率",
        "mlp": "ニューラルネット\n（グラフなし）", "gcn": "GCN", "sage": "GraphSAGE型"}
ORDER = ["ridge", "lgbm", "lgbm_nx", "lgbm_ny", "mlp", "gcn", "sage"]
SCH = {"random": "ランダムに分ける", "block": "都道府県ごとに分ける"}
C = {"random": "#4C78A8", "block": "#E45756"}
out = {}

# 1) 本体：モデル × 検証の分け方の R²
m = S[S.tag == "main"].set_index(["scheme", "model"])
fig, ax = plt.subplots(figsize=(10, 4.8))
x = np.arange(len(ORDER)); w = 0.38
for k, sc in enumerate(["random", "block"]):
    v = [m.loc[(sc, o), "r2"] for o in ORDER]; e = [m.loc[(sc, o), "r2_sd"] for o in ORDER]
    b = ax.bar(x + (k - 0.5) * w, v, w, yerr=e, color=C[sc], label=SCH[sc], capsize=2)
    for xi, vi in zip(x + (k - 0.5) * w, v):
        ax.text(xi, max(vi, 0) + 0.02, f"{vi:.2f}", ha="center", fontsize=8)
ax.set_xticks(x); ax.set_xticklabels([NAME[o] for o in ORDER], fontsize=8.5)
ax.set_ylabel("決定係数 R²（テスト側）"); ax.set_ylim(0, max(0.85, m.r2.max() + 0.1))
ax.set_title("市区町村の合計特殊出生率（2018〜22年）を8つの指標から予測したときの当たり方")
ax.legend(frameon=False); ax.grid(axis="y", alpha=0.3)
fig.text(0.01, 0.01, "1,841市区町村。ランダム5分割は3回、都道府県ごとの5分割は県の組み合わせを3通り。ひげは3回のばらつき（標準偏差）。", fontsize=7.5, color="gray")
fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(FIG / "fig1_models.png", dpi=150); plt.close(fig)
out["main"] = m.reset_index()[["scheme", "model", "rmse", "r2", "r2_sd"]].round(4).to_dict("records")

# 2) LightGBM からの改善幅（くり返しごとの差の平均と幅）
g = F[F.tag == "main"].groupby(["scheme", "model", "rep"]).agg(sse=("sse", "sum"), sst=("sst", "sum")).reset_index()
g["r2"] = 1 - g.sse / g.sst
base = g[g.model == "lgbm"].set_index(["scheme", "rep"]).r2
g["d"] = g.r2 - g.set_index(["scheme", "rep"]).index.map(base)
d = g.groupby(["scheme", "model"]).d.agg(["mean", "min", "max"]).reset_index()
out["gain_vs_lgbm"] = d.round(4).to_dict("records")
fig, ax = plt.subplots(figsize=(9, 4.6))
oo = [o for o in ORDER if o != "lgbm"]
for k, sc in enumerate(["random", "block"]):
    dd = d[d.scheme == sc].set_index("model").loc[oo]
    xs = np.arange(len(oo)) + (k - 0.5) * 0.38
    ax.bar(xs, dd["mean"], 0.38, color=C[sc], label=SCH[sc])
    ax.errorbar(xs, dd["mean"], yerr=[dd["mean"] - dd["min"], dd["max"] - dd["mean"]], fmt="none", ecolor="k", capsize=2, lw=0.8)
ax.axhline(0, color="k", lw=0.8)
ax.set_xticks(np.arange(len(oo))); ax.set_xticklabels([NAME[o] for o in oo], fontsize=8.5)
ax.set_ylabel("R² の差（各モデル − LightGBM）")
ax.set_title("LightGBM（グラフなし）と比べて、R² がどれだけ変わったか")
ax.legend(frameon=False); ax.grid(axis="y", alpha=0.3)
fig.text(0.01, 0.01, "ひげは3回のくり返しの最小〜最大。", fontsize=7.5, color="gray")
fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(FIG / "fig2_gain.png", dpi=150); plt.close(fig)

# 3) 頑健性：グラフの作り方・層の数・対象を変える
rows = []
for tag, lab in [("main", "隣接・2層"), ("graph_knn6", "近い6区域・2層"), ("layers1", "隣接・1層"), ("layers3", "隣接・3層")]:
    for mo in ["lgbm_nx", "gcn", "sage"]:
        for sc in ["random", "block"]:
            r = S[(S.tag == tag) & (S.model == mo) & (S.scheme == sc)]
            if len(r):
                rows.append({"setting": lab, "model": mo, "scheme": sc, "r2": r.r2.iloc[0]})
R3 = pd.DataFrame(rows)
out["robust_graph_layers"] = R3.round(4).to_dict("records")
fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.4), sharey=True)
sets = ["隣接・1層", "隣接・2層", "隣接・3層", "近い6区域・2層"]
mk = {"lgbm_nx": ("s", "#54A24B"), "gcn": ("o", "#F58518"), "sage": ("^", "#B279A2")}
for ax, sc in zip(axes, ["random", "block"]):
    for mo, (mm, cc) in mk.items():
        r = R3[(R3.model == mo) & (R3.scheme == sc)].set_index("setting").reindex(sets)
        ax.plot(range(len(sets)), r.r2, marker=mm, color=cc, label=NAME[mo].replace("\n", ""), lw=1.2)
    lg = S[(S.tag == "main") & (S.model == "lgbm") & (S.scheme == sc)].r2.iloc[0]
    ax.axhline(lg, color="gray", ls="--", lw=1); ax.text(len(sets) - 1, lg + 0.008, "LightGBM（グラフなし）", ha="right", fontsize=8, color="gray")
    ax.set_xticks(range(len(sets))); ax.set_xticklabels(sets, fontsize=8.5); ax.set_title(SCH[sc]); ax.grid(alpha=0.3)
axes[0].set_ylabel("決定係数 R²"); axes[0].legend(frameon=False, fontsize=8.5)
fig.suptitle("グラフの作り方と層の数を変えたときの当たり方")
fig.tight_layout(); fig.savefig(FIG / "fig3_robust.png", dpi=150); plt.close(fig)

# 4) 1都3県：隣接・近い6区域・通勤のグラフ
K = S[S.tag == "kanto"]
out["kanto"] = K[["graph", "scheme", "model", "r2", "r2_sd"]].round(4).to_dict("records")
GR = {"adjacent": "隣接", "knn6": "近い6区域", "commute_top6": "通勤の多い相手6つ", "commute_1pct": "通勤が人口の1%以上"}
fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), sharey=True)
mods = ["lgbm", "lgbm_nx", "lgbm_ny", "gcn", "sage"]
cols = ["#9D9D9D", "#54A24B", "#72B7B2", "#F58518", "#B279A2"]
for ax, sc in zip(axes, ["random", "block"]):
    for k, (mo, cc) in enumerate(zip(mods, cols)):
        v = [K[(K.graph == gname) & (K.scheme == sc) & (K.model == mo)].r2.iloc[0] for gname in GR]
        xs_ = np.arange(4) + (k - 2) * 0.16
        ax.bar(xs_, np.maximum(v, -0.8), 0.16, color=cc, label=NAME[mo].replace("\n", ""))
        for xi, vi in zip(xs_, v):
            if vi < -0.8:
                ax.text(xi, -0.78, f"{vi:.1f}", ha="center", va="bottom", fontsize=7, rotation=90)
    ax.set_xticks(range(4)); ax.set_xticklabels(GR.values(), fontsize=8.5); ax.axhline(0, color="k", lw=0.6)
    ax.set_title("市区町村をランダムに5分割" if sc == "random" else "都県ごとに1つずつ外す"); ax.grid(axis="y", alpha=0.3)
axes[0].set_ylabel("決定係数 R²"); axes[0].set_ylim(-0.8, 0.6); axes[0].legend(frameon=False, fontsize=7.5, ncol=2, loc="lower left")
fig.suptitle("1都3県（市区町村・区）だけで、どのつながりを使うと良いか")
fig.text(0.01, 0.01, "LightGBM（灰色）はグラフを使わないので、4つのグラフで同じ値。−0.8 より下は棒を切り、値を書いた。241市区町村・区。", fontsize=7.5, color="gray")
fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(FIG / "fig4_kanto.png", dpi=150); plt.close(fig)

# 5) 残差の空間的な偏り（Moran's I）と、どこで良くなったか
e = pd.read_csv(DATA / "edges_adjacent.csv")
codes = list(nodes.code); nb = {c: set() for c in codes}
for a, b in zip(e.i, e.j):
    nb[codes[a]].add(codes[b]); nb[codes[b]].add(codes[a])
w = W({c: sorted(v) for c, v in nb.items()}, id_order=codes, silence_warnings=True); w.transform = "r"
mor = []
for sc in ["random", "block"]:
    for mo in ORDER:
        q = P[(P.scheme == sc) & (P.model == mo)]
        res = q.assign(r=q.y - q.pred).groupby("code").r.mean().reindex(codes)
        np.random.seed(SEED)
        mi = Moran(res.values, w, permutations=999)
        mor.append({"scheme": sc, "model": mo, "moran_I": round(mi.I, 3), "p": round(mi.p_sim, 3)})
out["moran_residual"] = mor
fig, axes = plt.subplots(1, 2, figsize=(11, 5.2))
mo_df = pd.DataFrame(mor)
for k, sc in enumerate(["random", "block"]):
    v = mo_df[mo_df.scheme == sc].set_index("model").loc[ORDER].moran_I
    axes[0].bar(np.arange(len(ORDER)) + (k - 0.5) * 0.38, v, 0.38, color=C[sc], label=SCH[sc])
axes[0].set_xticks(range(len(ORDER))); axes[0].set_xticklabels([NAME[o] for o in ORDER], fontsize=7)
axes[0].axhline(0, color="k", lw=0.6); axes[0].set_ylabel("予測の外れ（残差）の Moran's I"); axes[0].legend(frameon=False, fontsize=8)
axes[0].set_title("外れが隣どうしで似ている度合い", fontsize=10); axes[0].grid(axis="y", alpha=0.3)
q = P[(P.scheme == "block")]
ab = q.assign(a=(q.y - q.pred).abs()).groupby(["code", "model"]).a.mean().unstack()
imp = (ab["lgbm"] - ab["sage"]).reindex(codes)
nd = nodes.set_index("code").loc[codes]
lim = np.nanpercentile(np.abs(imp), 95)
sc_ = axes[1].scatter(nd.x_km, nd.y_km, c=imp, cmap="RdBu", vmin=-lim, vmax=lim, s=4)
axes[1].set_aspect("equal"); axes[1].set_xticks([]); axes[1].set_yticks([])
axes[1].set_title("都道府県ごとに分けたとき、GraphSAGE型で外れが\n小さくなった区域（青）と大きくなった区域（赤）", fontsize=10)
plt.colorbar(sc_, ax=axes[1], shrink=0.7, label="外れの大きさの差（LightGBM − GraphSAGE型）")
out["block_sage_better_share"] = round(float((imp > 0).mean()), 3)
fig.tight_layout(); fig.savefig(FIG / "fig5_residual.png", dpi=150); plt.close(fig)

# 対象を変えた結果（高齢者の割合）は表だけ
A = S[S.tag == "target_aged"][["scheme", "model", "rmse", "r2", "r2_sd"]]
out["target_aged"] = A.round(4).to_dict("records")
json.dump(out, open(RES / "results.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1)[:6000])

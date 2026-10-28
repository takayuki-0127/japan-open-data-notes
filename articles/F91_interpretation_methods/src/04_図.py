"""04 図"""
import json
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import RES, METHODS, MCOL, L_LABEL, P_LABEL, save, GRAY, BLUE, ORANGE

LAB = {"地価": L_LABEL, "電力需要": P_LABEL}
S = json.load(open(RES / "summary.json"))
imp = {k: pd.read_csv(RES / f"importance_{k}.csv", index_col=0) for k in LAB}
lab = lambda k, f: LAB[k].get(f, f)

# 1 手法ごとの重要度の割合（上位10）
fig, axes = plt.subplots(1, 2, figsize=(11, 5.6))
for ax, k in zip(axes, LAB):
    s = imp[k][METHODS] / imp[k][METHODS].sum()
    top = s.rank(ascending=False).mean(axis=1).nsmallest(10).index[::-1]
    y = np.arange(len(top)); h = 0.2
    for i, m in enumerate(METHODS):
        ax.barh(y + (1.5 - i) * h, s.loc[top, m] * 100, h, color=MCOL[m], label=m)
    ax.set_yticks(y); ax.set_yticklabels([lab(k, f) for f in top], fontsize=9)
    ax.set_xlabel("重要度の割合（%、手法ごとに合計100）"); ax.set_title(k, fontsize=11)
    ax.grid(axis="x", alpha=.3); ax.spines[["top", "right"]].set_visible(False)
axes[0].legend(fontsize=8, loc="lower right")
fig.suptitle("同じモデルでも、手法で「効いている変数」の大きさは変わる（上位10、平均順位の順）", fontsize=12)
fig.tight_layout(); save(fig, "f91_rank_compare.png")

# 2 手法どうしの順位相関
fig, axes = plt.subplots(1, 2, figsize=(10, 4.4))
short = ["SHAP", "並べ替え", "PDP", "ALE"]
for ax, k in zip(axes, LAB):
    M = imp[k][METHODS].rank().corr(method="pearson").values
    ax.imshow(M, vmin=0, vmax=1, cmap="Blues")
    for i in range(4):
        for j in range(4):
            ax.text(j, i, f"{M[i, j]:.2f}", ha="center", va="center", fontsize=10, color="white" if M[i, j] > .7 else "black")
    ax.set_xticks(range(4)); ax.set_yticks(range(4)); ax.set_xticklabels(short); ax.set_yticklabels(short)
    t5 = S[k]["compare"]
    ov = np.mean([v["top5_overlap"] for v in t5.values()])
    ax.set_title(f"{k}（変数{len(imp[k])}個）　上位5の重なり 平均{ov:.1f}/5", fontsize=10)
fig.suptitle("順位の相関（スピアマン）：全体の並びはおおむねそろう", fontsize=12)
fig.tight_layout(); save(fig, "f91_rankcorr.png")

# 3 PDP と ALE
fig, axes = plt.subplots(1, 3, figsize=(12, 4))
for ax, (k, f) in zip(axes, [("電力需要", "temp_mean"), ("電力需要", "temp_max"), ("地価", "log_pass_3km")]):
    c = pd.read_csv(RES / f"curves_{k}.csv")
    for kind, col, nm in [("pdp", MCOL["部分依存（PDP）"], "部分依存（PDP）"), ("ale", MCOL["ALE"], "ALE")]:
        d = c[(c.feature == f) & (c.kind == kind)]
        v = d.value - d.value.mean()
        ax.plot(d.x, v, "-o", ms=3, color=col, label=nm)
    ax.axhline(0, color=GRAY, lw=.8)
    unit = "MW" if k == "電力需要" else "log(価格)"
    ax.set_title(f"{k}：{lab(k, f)}", fontsize=10); ax.set_ylabel(f"予測への効果（{unit}、平均0）")
    ax.grid(alpha=.3); ax.spines[["top", "right"]].set_visible(False)
axes[0].legend(fontsize=8)
fig.suptitle("相関する変数があると、PDP と ALE の曲線の傾きが変わる", fontsize=12)
fig.tight_layout(); save(fig, "f91_pdp_ale.png")

# 4 相関する仲間を外したとき
fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
for ax, k in zip(axes, LAB):
    D = S[k]["drop"]
    x = np.arange(4); w = .27
    ax.bar(x - w, [D["keep_share_before"][m] * 100 for m in METHODS], w, color=GRAY, label=f"{lab(k, D['keep'])}だけ（外す前）")
    ax.bar(x, [D["group_share_before"][m] * 100 for m in METHODS], w, color="#cfcfcf", label="仲間を合わせた合計（外す前）")
    ax.bar(x + w, [D["keep_share_after"][m] * 100 for m in METHODS], w, color=[MCOL[m] for m in METHODS], label=f"{lab(k, D['keep'])}（仲間を外した後・色つき）")
    ax.set_xticks(x); ax.set_xticklabels(short); ax.set_ylabel("重要度の割合（%）")
    ax.set_title(f"{k}：{lab(k, D['keep'])}と相関する{len(D['dropped'])}変数を外す", fontsize=10)
    ax.legend(fontsize=7.5); ax.grid(axis="y", alpha=.3); ax.spines[["top", "right"]].set_visible(False)
fig.suptitle("相関する仲間がいると、重要度は仲間に分けられる（外すと1つに集まる）", fontsize=12)
fig.tight_layout(); save(fig, "f91_corr_shift.png")

# 5 シミュレーション
d = pd.read_csv(RES / "simulation.csv")
dn = pd.read_csv(RES / "simulation_n.csv")
fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
for m in METHODS:
    g = d[d.method == m].groupby("rho")
    axes[0].plot(g.x2.mean().index, g.x2.mean() * 100, "-o", color=MCOL[m], label=m)
axes[0].plot(g.x4.mean().index, d.groupby("rho").x4.mean() * 100, "--", color=GRAY, label="まったく関係ない x4（4手法の平均）")
axes[0].set_title("効果0の x2 に付いた重要度（%、学習4000件・8回の平均）", fontsize=10)
axes[0].set_xlabel("x1 と x2 の相関")
q = dn[dn.rho == 0.99].assign(ex=lambda t: (t.x2 - t.x4) * 100).groupby(["method", "n_train"]).ex.mean()
ns = [500, 2000, 20000]; w = .2
for i, m in enumerate(METHODS):
    axes[1].bar(np.arange(3) + (i - 1.5) * w, [q[(m, n)] for n in ns], w, color=MCOL[m], label=m)
axes[1].set_xticks(range(3)); axes[1].set_xticklabels([f"{n:,}件" for n in ns]); axes[1].set_xlabel("学習データの件数（相関0.99）")
axes[1].set_title("x2 の重要度 − 関係ない x4 の重要度（%ポイント）", fontsize=10)
for ax in axes:
    ax.grid(alpha=.3); ax.spines[["top", "right"]].set_visible(False)
axes[0].legend(fontsize=7.5)
fig.suptitle("答えが分かっている人工データ：相関が0.99まで強まり、データが少ないと、効果のない変数にも重要度が付く", fontsize=11.5)
fig.tight_layout(); save(fig, "f91_sim.png")

# 6 頑健性
fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), sharey=True)
for ax, k in zip(axes, LAB):
    r = pd.read_csv(RES / f"robust_{k}.csv")
    r = r[r.method != "手法どうし（平均）"]
    sets = list(dict.fromkeys(r.setting))
    for i, st in enumerate(sets):
        q = r[r.setting == st]
        for _, row in q.iterrows():
            ax.scatter(row.spearman_vs_base, i + (METHODS.index(row.method) - 1.5) * .12, color=MCOL[row.method], s=40,
                       label=row.method if i == 0 or st.startswith("SHAP") else None)
    ax.set_yticks(range(len(sets))); ax.set_yticklabels(sets, fontsize=8.5); ax.set_xlim(0.4, 1.02)
    ax.axvline(1, color=GRAY, lw=.8); ax.set_xlabel("基本の設定との順位相関"); ax.set_title(k, fontsize=10)
    ax.grid(axis="x", alpha=.3); ax.spines[["top", "right"]].set_visible(False)
h, l = axes[0].get_legend_handles_labels(); u = dict(zip(l, h))
axes[1].legend(u.values(), u.keys(), fontsize=8, loc="lower left")
fig.suptitle("頑健性：モデルや計算の設定を変えても、各手法の順位はどれだけ保たれるか", fontsize=12)
fig.tight_layout(); save(fig, "f91_robust.png")
print("ok")

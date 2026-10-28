"""04 図：results/ の結果から figures/ の図を作る。"""
import json
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

matplotlib.use("Agg")
plt.rcParams["font.family"] = "Noto Sans CJK JP"
plt.rcParams["axes.unicode_minus"] = False
ROOT = Path(__file__).resolve().parents[1]
RES, FIG = ROOT / "results", ROOT / "figures"
FIG.mkdir(exist_ok=True)
R = json.load(open(RES / "results.json"))
C = ["#2f6f9f", "#e07b39", "#5aa469", "#b04a5a", "#7b6fb0", "#888888"]
SIZE_LBL = ["小さい町\n（中央値{}人）", "{}人", "{}人", "{}人", "大きい市\n（{}人）"]


def size_labels(by):
    out = []
    for i, b in enumerate(by):
        v = int(round(b["pop_median"], -2))
        out.append(SIZE_LBL[i].format(f"{v:,}"))
    return out


# 図1：実データ。人口の変化と店の変化（2012→2021）
d = pd.read_csv(RES / "abm_2012_2021_by_town.csv")
d = d[d.rep == 0]
fig, ax = plt.subplots(figsize=(7.2, 5.4))
for q in range(5):
    g = d[d.size_q == q]
    ax.scatter(g.dp * 100, g.ds * 100, s=6, alpha=.45, color=C[q], label=["小さい町", "", "", "", "大きい市"][q] or None)
lim = [-40, 15]
ax.plot(lim, lim, color="k", lw=1, ls="--", label="人口と同じ割合で減る線")
b = R["real"]["beta_all"]
xx = np.linspace(-40, 15, 10)
ax.plot(xx, b[2] * 100 + b[0] * xx, color="#b04a5a", lw=2, label=f"当てはめた直線（傾き {b[0]:.2f}）")
ax.set_xlim(-40, 15); ax.set_ylim(-80, 60)
ax.set_xlabel("人口の変化（%、対数差×100、2012→2021）")
ax.set_ylabel("小売の事業所数の変化（%、対数差×100）")
ax.set_title("図1　店の数は、ほぼ人口と同じ割合で減っていた（1,734市区町村）", fontsize=11)
ax.legend(fontsize=8, loc="upper left")
ax.grid(alpha=.3)
fig.tight_layout(); fig.savefig(FIG / "fig1_real_stores_vs_pop.png", dpi=150); plt.close(fig)

# 図2：照合。人口が1%減ると店は何%減るか（傾き）を、規模別に実データと ABM で比べる
by = R["real"]["by_size"]
lbl = size_labels(by)
real_b = [x["beta"] for x in by]
abm_b = R["validation"]["beta_by_size_mean"]
fig, ax = plt.subplots(figsize=(7.6, 4.6))
xi = np.arange(5)
ax.bar(xi - .2, real_b, .38, color=C[0], label="実データ（2012→2021）")
ax.bar(xi + .2, abm_b, .38, color=C[1], label="ABM（同じ期間・同じ人口の変化）")
ax.axhline(1, color="k", lw=1, ls="--")
ax.text(4.45, 1.02, "人口と同じ割合", ha="right", fontsize=8)
ax.set_xticks(xi); ax.set_xticklabels(lbl, fontsize=8)
ax.set_ylabel("傾き（人口が1%減ると店が何%減るか）")
v = R["validation"]
ax.set_title(f"図2　規模別の傾き：実データ と ABM（全体では 実データ {R['real']['beta_all'][0]:.2f}、ABM {v['beta_mean']:.2f}）", fontsize=10)
ax.legend(fontsize=8); ax.grid(axis="y", alpha=.3)
fig.tight_layout(); fig.savefig(FIG / "fig2_validation_by_size.png", dpi=150); plt.close(fig)

# 図3：2050年への投影。規模別の人口と店の変化、近くに店がない住民の割合
pb = R["projection_base"]["by_size"]
fig, axes = plt.subplots(1, 2, figsize=(10, 4.4))
ax = axes[0]
ax.bar(xi - .2, [100 * (np.exp(x["dp50"]) - 1) for x in pb], .38, color=C[5], label="人口（社人研の推計）")
ax.bar(xi + .2, [100 * (np.exp(x["ds50"]) - 1) for x in pb], .38, color=C[1], label="店の数（ABM）")
ax.set_xticks(xi); ax.set_xticklabels(lbl, fontsize=7)
ax.set_ylabel("2020→2050 の変化（%）"); ax.legend(fontsize=8); ax.grid(axis="y", alpha=.3)
ax.set_title("人口と店の数の変化", fontsize=10)
ax = axes[1]
ax.plot(xi, [100 * x["acc1_0"] for x in pb], "o-", color=C[0], label="2020（1km 以内に店がない）")
ax.plot(xi, [100 * x["acc1_1"] for x in pb], "o--", color=C[0], alpha=.7, label="2050（同）")
ax.plot(xi, [100 * x["acc2_0"] for x in pb], "s-", color=C[3], label="2020（2km 以内に店がない）")
ax.plot(xi, [100 * x["acc2_1"] for x in pb], "s--", color=C[3], alpha=.7, label="2050（同）")
ax.set_xticks(xi); ax.set_xticklabels(lbl, fontsize=7)
ax.set_ylabel("住民の割合（%、モデルの中の距離）"); ax.legend(fontsize=7); ax.grid(alpha=.3)
ax.set_title("近くに店がない住民の割合（モデルの中）", fontsize=10)
fig.suptitle("図3　2050年への投影（基準の前提）", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "fig3_projection_2050.png", dpi=150); plt.close(fig)

# 図4：前提を変えると、小さい町の答えはどれだけ動くか
sc = pd.DataFrame(R["scenarios"])
sv = pd.DataFrame(R["scenario_validation"])
sc = sc.merge(sv, on="scenario", how="left")
fig, axes = plt.subplots(1, 3, figsize=(12, 5.2), sharey=True)
yi = np.arange(len(sc))[::-1]
axes[0].barh(yi, 100 * (np.exp(sc.small_ds50) - 1), color=C[1])
axes[0].axvline(100 * (np.exp(sc.small_dp50.mean()) - 1), color="k", ls="--", lw=1)
axes[0].set_title("小さい町の店の数の変化\n（2020→2050、%。点線は人口）", fontsize=9)
axes[1].barh(yi, 100 * sc.small_acc1_1, color=C[0])
axes[1].axvline(100 * sc.small_acc1_0.mean(), color="k", ls="--", lw=1)
axes[1].set_title("小さい町で 1km 以内に店がない住民\n（2050、%。点線は2020）", fontsize=9)
axes[2].barh(yi, sc.beta_2012_2021, color=C[2])
axes[2].axvline(R["real"]["beta_all"][0], color="k", ls="--", lw=1)
axes[2].set_title("同じ前提で 2012→2021 を再現した傾き\n（点線は実データ 0.95）", fontsize=9)
axes[0].set_yticks(yi); axes[0].set_yticklabels(sc.scenario, fontsize=8)
for a in axes:
    a.grid(axis="x", alpha=.3)
fig.suptitle("図4　前提を変えたときの答え（規模別に選んだ400市区町村、各2回の平均）", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "fig4_scenarios.png", dpi=150); plt.close(fig)

# 図5：架空の町で50年（人口が7割減る）。店の数の推移
s = pd.read_csv(RES / "synthetic_long_summary.csv")
fig, axes = plt.subplots(1, 3, figsize=(12, 4.2))
for a, p0 in zip(axes, [1000, 3000, 10000]):
    g0 = s[s.pop0 == p0]
    for j, name in enumerate(["基準", "余裕が小さい", "町の外の伸び +2%/年", "赤字1年で閉店"]):
        g = g0[g0.scenario == name]
        a.plot(g.year, g.n, color=C[j], label=name)
        if name == "基準":
            a.fill_between(g.year, g.n_lo, g.n_hi, color=C[j], alpha=.15)
    gb = g0[g0.scenario == "基準"]
    a.plot(gb.year, gb.n.iloc[0] * gb["pop"] / gb["pop"].iloc[0], color="k", ls="--", lw=1, label="人口と同じ割合")
    a.set_title(f"最初の人口 {p0:,}人", fontsize=10)
    a.set_xlabel("年（人口は50年で3割に）"); a.grid(alpha=.3)
axes[0].set_ylabel("店の数（20回の平均。帯は基準の10〜90%）")
axes[0].legend(fontsize=7)
fig.suptitle("図5　架空の町で、人口が少しずつ減ると店はどう減るか", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "fig5_synthetic_towns.png", dpi=150); plt.close(fig)
print("figures saved")

"""図を作る（6枚）。"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch
from common import DATA, RES, FIG

d = pd.read_csv(DATA / "pref_panel.csv", index_col="pref_code")
main = pd.read_csv(RES / "coef_by_adjustment_set.csv")
spec = pd.read_csv(RES / "specification_curve.csv")
rob = pd.read_csv(RES / "robustness.csv")
eff = pd.read_csv(RES / "variable_inclusion_effect.csv")
SEX = {"m": "男性", "f": "女性"}; COL = {"m": "#2f6db3", "f": "#c4504a"}
LBL = {"did": "都市化（人口集中地区の割合）", "income": "所得", "univ_grad": "大卒の割合", "aged65": "高齢化率",
       "temp": "年平均気温", "unemp": "失業率", "beds": "病床数", "universities": "大学数", "std_mort": "標準化死亡率"}

# 1. DAG
pos = {"doctors": (0.15, 0.45), "e0": (0.85, 0.45), "did": (0.5, 0.95), "income": (0.32, 0.76), "univ_grad": (0.68, 0.76),
       "aged65": (0.5, 0.62), "universities": (0.08, 0.85), "temp": (0.95, 0.85), "unemp": (0.82, 0.95),
       "beds": (0.5, 0.18), "std_mort": (0.95, 0.12)}
name = {"doctors": "医師数\n（原因の候補）", "e0": "平均寿命\n（結果）", **{k: v.replace("（人口集中地区の割合）", "") for k, v in LBL.items()}}
kind = {"doctors": "#333333", "e0": "#333333", "did": "#e08a1e", "income": "#e08a1e", "univ_grad": "#e08a1e", "aged65": "#e08a1e",
        "temp": "#3c9a5b", "unemp": "#3c9a5b", "universities": "#8a63b5", "beds": "#7a7a7a", "std_mort": "#b33a3a"}
edges = [("did", "doctors"), ("did", "e0"), ("did", "income"), ("did", "univ_grad"), ("did", "universities"), ("did", "aged65"),
         ("did", "unemp"), ("income", "doctors"), ("income", "e0"), ("univ_grad", "doctors"), ("univ_grad", "e0"),
         ("universities", "doctors"), ("aged65", "doctors"), ("aged65", "e0"), ("temp", "e0"), ("unemp", "e0"),
         ("doctors", "e0"), ("e0", "std_mort"), ("doctors", "beds"), ("beds", "e0")]
fig, ax = plt.subplots(figsize=(9.5, 6.2))
for a, b in edges:
    st = "--" if "beds" in (a, b) else "-"
    ax.add_patch(FancyArrowPatch(pos[a], pos[b], arrowstyle="-|>", mutation_scale=14, lw=2.2 if (a, b) == ("doctors", "e0") else 1.1,
                                 color="#222" if (a, b) == ("doctors", "e0") else "#999", linestyle=st, shrinkA=26, shrinkB=26))
for k, (x, y) in pos.items():
    ax.text(x, y, name[k], ha="center", va="center", fontsize=10.5, color="white", fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.45", fc=kind[k], ec="none"))
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color="#e08a1e", label="調整が必要（DAGの最小セット）"), Patch(color="#3c9a5b", label="結果だけに効く（入れると精度が上がる）"),
                   Patch(color="#8a63b5", label="医師数にだけ効く（入れなくてよい）"), Patch(color="#7a7a7a", label="病床数（中間か共通原因か、仮定で変わる）"),
                   Patch(color="#b33a3a", label="結果の一部（入れてはいけない）")], loc="lower center", bbox_to_anchor=(0.5, -0.2), ncol=2, fontsize=9, frameon=False)
ax.set_xlim(-0.02, 1.07); ax.set_ylim(0.0, 1.05); ax.axis("off")
ax.set_title("仮定した因果の図（DAG）：医師数と平均寿命のあいだの「裏口」をふさぐ変数を選ぶ", fontsize=12)
fig.tight_layout(); fig.savefig(FIG / "f65_dag.png", bbox_inches="tight"); plt.close(fig)

# 2. 散布図
fig, axes = plt.subplots(1, 2, figsize=(10, 4.3))
for ax, s in zip(axes, ("m", "f")):
    x, y = d["doctors"], d[f"e0_{s}_2015"]
    ax.scatter(x, y, s=28, color=COL[s], alpha=0.8)
    b = np.polyfit(x, y, 1); xx = np.linspace(x.min(), x.max(), 50); ax.plot(xx, np.polyval(b, xx), color="#333", lw=1.2)
    r = np.corrcoef(x, y)[0, 1]
    ax.set_title(f"{SEX[s]}：相関 {r:.2f}（47都道府県）", fontsize=11)
    ax.set_xlabel("医療施設に従事する医師数（人口10万人当たり、2010年）"); ax.set_ylabel("平均寿命（2015年、年）"); ax.grid(alpha=0.3)
fig.suptitle("医師が多い県ほど平均寿命が長い？ 女性ではゆるい右上がり、男性ではほぼ関係なし", fontsize=12)
fig.tight_layout(); fig.savefig(FIG / "f65_scatter.png"); plt.close(fig)

# 3. 調整のしかた別の係数
sets = list(dict.fromkeys(main["set"]))
fig, ax = plt.subplots(figsize=(10, 5.6))
for j, s in enumerate(("m", "f")):
    g = main[main.sex == s].set_index("set").loc[sets]
    yy = np.arange(len(sets)) + (j - 0.5) * 0.3
    ax.errorbar(g.coef, yy, xerr=[g.coef - g.lo, g.hi - g.coef], fmt="o", color=COL[s], capsize=3, label=SEX[s])
ax.axvline(0, color="#555", lw=1)
ax.set_yticks(np.arange(len(sets))); ax.set_yticklabels(sets, fontsize=9.5); ax.invert_yaxis()
ax.set_xlabel("医師が人口10万人当たり50人多いときの平均寿命の差（年）と95%区間")
ax.set_title("どの変数で調整するかで、答えはどれだけ変わるか", fontsize=12); ax.legend(); ax.grid(axis="x", alpha=0.3)
fig.tight_layout(); fig.savefig(FIG / "f65_sets.png"); plt.close(fig)

# 4. すべての組み合わせ（256通り）
fig, axes = plt.subplots(1, 2, figsize=(11, 4.4), sharey=True)
for ax, s in zip(axes, ("m", "f")):
    g = spec[spec.sex == s].sort_values("coef").reset_index(drop=True)
    ok = g.valid_A | g.valid_B
    ax.fill_between(g.index, g.lo, g.hi, color="#ccc", alpha=0.6, lw=0)
    ax.scatter(g.index[~ok], g.coef[~ok], s=8, color="#999", label="DAGで「足りない／余計」な組み合わせ")
    ax.scatter(g.index[ok], g.coef[ok], s=30, color=COL[s], label="DAGで正しい組み合わせ（A・B）", zorder=3)
    ax.axhline(0, color="#555", lw=1)
    ax.set_title(f"{SEX[s]}：8変数の入れ方256通り（{g.coef.min():.2f}〜{g.coef.max():.2f}年）", fontsize=11)
    ax.set_xlabel("係数の小さい順"); ax.grid(alpha=0.3)
axes[0].set_ylabel("50人多いときの平均寿命の差（年）"); axes[1].legend(fontsize=8.5, loc="upper left")
fig.suptitle("変数の入れ方を全部試すと答えは大きく揺れる。DAGで選ぶと幅が狭まる", fontsize=12)
fig.tight_layout(); fig.savefig(FIG / "f65_spec.png"); plt.close(fig)

# 5. 頑健性
order = list(dict.fromkeys(rob.check))
fig, ax = plt.subplots(figsize=(10, 6.4))
for j, s in enumerate(("m", "f")):
    g = rob[rob.sex == s].set_index("check").loc[order]
    yy = np.arange(len(order)) + (j - 0.5) * 0.3
    ax.errorbar(g.coef, yy, xerr=[g.coef - g.lo, g.hi - g.coef], fmt="o", color=COL[s], capsize=3, label=SEX[s])
ax.axvline(0, color="#555", lw=1); ax.set_yticks(np.arange(len(order))); ax.set_yticklabels(order, fontsize=8.8); ax.invert_yaxis()
ax.set_xlabel("50人多い（増えた）ときの平均寿命の差（年）と95%区間"); ax.legend(); ax.grid(axis="x", alpha=0.3)
ax.set_title("年・結果・比べ方を変えた確認", fontsize=12)
fig.tight_layout(); fig.savefig(FIG / "f65_robust.png"); plt.close(fig)

# 6. 入れると係数が動く変数
fig, ax = plt.subplots(figsize=(9, 4.3))
vs = list(LBL)[:8]; x = np.arange(len(vs))
for j, s in enumerate(("m", "f")):
    g = eff[eff.sex == s].set_index("var").loc[vs]
    ax.bar(x + (j - 0.5) * 0.38, g["diff"], width=0.38, color=COL[s], label=SEX[s])
ax.axhline(0, color="#555", lw=1); ax.set_xticks(x); ax.set_xticklabels([LBL[v].replace("（人口集中地区の割合）", "") for v in vs], fontsize=9.5)
ax.set_ylabel("入れたときの係数の平均 − 入れないとき（年）"); ax.legend(); ax.grid(axis="y", alpha=0.3)
ax.set_title("256通りのうち、その変数を入れると係数はどれだけ動くか", fontsize=12)
fig.tight_layout(); fig.savefig(FIG / "f65_inclusion.png"); plt.close(fig)
print(sorted(p.name for p in FIG.glob("*.png")))

"""778 件数のそろわない2元配置で、平方和の型（I・II・III）を変えると、有意の見え方はどれだけ変わるのか

架空の店の実験。要因 A（売り場の配置：2通り）と要因 B（時間帯：3通り）。
各組の件数をそろえず、A＝1 は B＝3 に、A＝2 は B＝1 に件数が偏るようにする（合計約240件）。
場面1：A は効かない・B だけ効く・交互作用なし。場面2：A も B も効き、交互作用もある。
statsmodels の anova_lm で Type I（A を先・B を先）・Type II・Type III（和が0の対比）の平方和を出し、
A が有意（5%）になる割合を比べる。各300回。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import statsmodels.formula.api as smf
from statsmodels.stats.anova import anova_lm
from common import RES, save, BLUE, ORANGE, GRAY, GREEN

SRC = "出典：架空のデータ（作成者が乱数で作成、seed 778）"
rng = np.random.default_rng(778)
R = 300
CNT = {(1, 1): 10, (1, 2): 30, (1, 3): 80, (2, 1): 80, (2, 2): 30, (2, 3): 10}
BEFF = {1: 0.0, 2: 0.5, 3: 1.0}


def make(scene):
    rows = []
    for (a, b), n in CNT.items():
        mu = BEFF[b]
        if scene == 2:
            mu += 0.3 * (a == 2) + (0.6 if (a == 2 and b == 3) else 0)
        rows.append(pd.DataFrame({"A": a, "B": b, "y": mu + rng.standard_normal(n)}))
    return pd.concat(rows, ignore_index=True)


def pvals(df):
    o = {}
    m1 = smf.ols("y ~ C(A) * C(B)", df).fit(); m2 = smf.ols("y ~ C(B) * C(A)", df).fit()
    o["I_Afirst"] = anova_lm(m1, typ=1).loc["C(A)", "PR(>F)"]
    o["I_Bfirst"] = anova_lm(m2, typ=1).loc["C(A)", "PR(>F)"]
    o["II"] = anova_lm(m1, typ=2).loc["C(A)", "PR(>F)"]
    m3 = smf.ols("y ~ C(A, Sum) * C(B, Sum)", df).fit()
    o["III"] = anova_lm(m3, typ=3).loc["C(A, Sum)", "PR(>F)"]
    return o


rows = []
for scene in [1, 2]:
    for r in range(R):
        p = pvals(make(scene)); p.update(scene=scene, rep=r); rows.append(p)
D = pd.DataFrame(rows); D.to_csv(RES / "reps.csv", index=False, float_format="%.6f")
K = ["I_Afirst", "I_Bfirst", "II", "III"]
S = D.groupby("scene")[K].agg(lambda s: (s < .05).mean()).reset_index()
S.to_csv(RES / "summary.csv", index=False)
ex = make(1)
cell = ex.groupby(["A", "B"]).y.agg(["size", "mean"]).reset_index(); cell.to_csv(RES / "example_cells.csv", index=False)
mA = ex.groupby("A").y.mean()
out = {"reps": R, "cell_counts": {f"A{a}B{b}": n for (a, b), n in CNT.items()},
       "scene1_sigA": {k: round(float(S[S.scene == 1][k].iloc[0]), 3) for k in K},
       "scene2_sigA": {k: round(float(S[S.scene == 2][k].iloc[0]), 3) for k in K},
       "example_raw_mean_A1": float(mA[1]), "example_raw_mean_A2": float(mA[2])}
json.dump(out, open(RES / "a778_main.json", "w"), ensure_ascii=False, indent=1)

lab = ["Type I\n（A を先）", "Type I\n（B を先）", "Type II", "Type III"]; x = np.arange(4)
# 図1：場面1
fig, ax = plt.subplots(figsize=(9, 4.6))
v = [out["scene1_sigA"][k] * 100 for k in K]
b = ax.bar(lab, v, color=[ORANGE, BLUE, GREEN, GRAY])
for bb, vv in zip(b, v): ax.text(bb.get_x() + bb.get_width() / 2, vv + 1.5, f"{vv:.0f}%", ha="center")
ax.axhline(5, color="black", ls="--", lw=1)
ax.set_ylabel("A が有意になった割合（%）"); ax.set_ylim(0, 105)
ax.set_title("場面1（A は効かない）：Type I で A を先に置くと、B の効きを A が取る")
save(fig, "a778_scene1.png", SRC)
# 図2：場面2
fig, ax = plt.subplots(figsize=(9, 4.6))
v = [out["scene2_sigA"][k] * 100 for k in K]
b = ax.bar(lab, v, color=[ORANGE, BLUE, GREEN, GRAY])
for bb, vv in zip(b, v): ax.text(bb.get_x() + bb.get_width() / 2, vv + 1.5, f"{vv:.0f}%", ha="center")
ax.set_ylabel("A が有意になった割合（%）"); ax.set_ylim(0, 105)
ax.set_title("場面2（A も効き、交互作用もある）：型によって A の有意の見え方が変わる")
save(fig, "a778_scene2.png", SRC)
# 図3：件数の偏りと平均
fig, axs = plt.subplots(1, 2, figsize=(10, 4))
for a, c in [(1, BLUE), (2, ORANGE)]:
    s = cell[cell.A == a]
    axs[0].bar(s.B + (a - 1.5) * .35, s["size"], .35, color=c, label=f"A={a}")
    axs[1].plot(s.B, s["mean"], "o-", color=c, label=f"A={a}")
axs[0].set_xticks([1, 2, 3]); axs[0].set_xlabel("B（時間帯）"); axs[0].set_ylabel("件数"); axs[0].legend(frameon=False)
axs[0].set_title("組ごとの件数の偏り", fontsize=11)
axs[1].set_xticks([1, 2, 3]); axs[1].set_xlabel("B（時間帯）"); axs[1].set_ylabel("平均（場面1の1回分）"); axs[1].legend(frameon=False)
axs[1].set_title(f"A の単純な平均：A=1 {mA[1]:.2f}、A=2 {mA[2]:.2f}", fontsize=11)
fig.suptitle("場面1：A は効かないが、A=1 は B=3（効きが大きい）に偏る", y=1.03)
save(fig, "a778_cells.png", SRC, y=-0.05)
print(json.dumps(out, ensure_ascii=False, indent=1))

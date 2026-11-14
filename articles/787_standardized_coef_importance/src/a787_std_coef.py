"""787 標準化した係数の大きさで変数の大事さを並べると、データのばらつき方でどれだけ順位が変わるのか

架空のデータ。y = 1.0·x1 + 1.5·x2 + 2.0·x3 + ばらつき（sd 2）。1単位あたりの効き方は x3 がいちばん大きい。
同じ式から、x のばらつき方だけが違う2つのデータを作る。
  データA：x の標準偏差 (2, 1, 0.5)　　データB：(0.5, 1, 2)
件数300で各300回、ふつうの係数・標準化係数・並べ替えの重要度（列を混ぜて誤差がどれだけ増えるか）で
3つの変数を並べ、1位になる変数の割合を比べる。あわせて x1 の標準偏差だけを0.25〜4に変えたときの順位を見る。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GRAY, GREEN, LIGHT

SRC = "出典：架空のデータ（作成者が乱数で作成、seed 787）"
rng = np.random.default_rng(787)
N, R = 300, 300
B = np.array([1.0, 1.5, 2.0])
SETS = {"A": [2, 1, .5], "B": [.5, 1, 2]}


def one(sds):
    X = rng.standard_normal((N, 3)) * np.array(sds)
    y = X @ B + rng.normal(0, 2, N)
    Xc = np.column_stack([np.ones(N), X]); b = np.linalg.lstsq(Xc, y, rcond=None)[0][1:]
    std = b * X.std(0, ddof=1) / y.std(ddof=1)
    pred = Xc @ np.r_[0, b] + (y.mean() - (X @ b).mean())
    base = np.mean((y - pred) ** 2); perm = []
    for j in range(3):
        Xp = X.copy(); Xp[:, j] = rng.permutation(Xp[:, j])
        perm.append(np.mean((y - (Xp @ b + (y.mean() - (X @ b).mean()))) ** 2) - base)
    return b, std, np.array(perm)


rows = []; ex = {}
for name, sds in SETS.items():
    res = [one(sds) for _ in range(R)]
    for mi, m in enumerate(["raw", "std", "perm"]):
        v = np.array([r[mi] for r in res])
        top = np.bincount(v.argmax(1), minlength=3) / R
        rows.append(dict(data=name, measure=m, **{f"mean_x{j+1}": v[:, j].mean() for j in range(3)}, **{f"top_x{j+1}": top[j] for j in range(3)}))
S = pd.DataFrame(rows); S.to_csv(RES / "summary.csv", index=False)

# x1 の標準偏差だけを変える
sweep = []
for s1 in [.25, .5, 1, 1.5, 2, 3, 4]:
    res = [one([s1, 1, 1]) for _ in range(R // 3)]
    std = np.array([r[1] for r in res]); raw = np.array([r[0] for r in res])
    rank_std = (std >= std[:, [0]]).sum(1).mean()          # x1 の順位（1が最上位）
    rank_raw = (raw >= raw[:, [0]]).sum(1).mean()
    sweep.append(dict(sd_x1=s1, std_x1=std[:, 0].mean(), std_x3=std[:, 2].mean(), rank_std_x1=rank_std, rank_raw_x1=rank_raw))
W = pd.DataFrame(sweep); W.to_csv(RES / "sweep_sd_x1.csv", index=False)

g = lambda d, m, c: float(S[(S.data == d) & (S.measure == m)][c].iloc[0])
out = {"n": N, "reps": R, "true_b": B.tolist(), "sds": SETS,
       "raw_top_x3": {d: g(d, "raw", "top_x3") for d in SETS}, "std_top_x1": {d: g(d, "std", "top_x1") for d in SETS},
       "std_top_x3": {d: g(d, "std", "top_x3") for d in SETS}, "perm_top_x1": {d: g(d, "perm", "top_x1") for d in SETS},
       "perm_top_x3": {d: g(d, "perm", "top_x3") for d in SETS},
       "std_means": {d: [round(g(d, "std", f"mean_x{j}"), 3) for j in (1, 2, 3)] for d in SETS},
       "raw_means": {d: [round(g(d, "raw", f"mean_x{j}"), 3) for j in (1, 2, 3)] for d in SETS},
       "sweep": W.round(3).to_dict(orient="records")}
json.dump(out, open(RES / "a787_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：2つのデータでの3つの物差し
fig, axs = plt.subplots(1, 3, figsize=(11, 3.9))
for ax, m, t in zip(axs, ["raw", "std", "perm"], ["ふつうの係数（1単位あたり）", "標準化係数", "並べ替えの重要度"]):
    for k, (d, c) in enumerate([("A", BLUE), ("B", ORANGE)]):
        v = [g(d, m, f"mean_x{j}") for j in (1, 2, 3)]
        ax.bar(np.arange(3) + (k - .5) * .38, v, .38, color=c, label=f"データ{d}")
    ax.set_xticks(range(3)); ax.set_xticklabels(["x1", "x2", "x3"]); ax.set_title(t, fontsize=11)
axs[0].legend(frameon=False)
fig.suptitle("同じ式でも、標準化係数と重要度の並びは x のばらつき方で逆になる（300回の平均）", y=1.03)
save(fig, "a787_three_measures.png", SRC, y=-0.05)

# 図2：1位になる変数の割合
fig, ax = plt.subplots(figsize=(9, 4.4)); labels = []; k = 0
for m, t in [("raw", "ふつうの係数"), ("std", "標準化係数"), ("perm", "並べ替えの重要度")]:
    for d in SETS:
        left = 0
        for j, c in zip((1, 2, 3), [GRAY, LIGHT, GREEN]):
            v = g(d, m, f"top_x{j}"); ax.barh(k, v, left=left, color=c, label=f"x{j} が1位" if k == 0 else None)
            if v > .08: ax.text(left + v / 2, k, f"{v:.0%}", ha="center", va="center", fontsize=9)
            left += v
        labels.append(f"{t}・データ{d}"); k += 1
ax.set_yticks(range(k)); ax.set_yticklabels(labels); ax.invert_yaxis(); ax.set_xlim(0, 1)
ax.set_xlabel("300回のうち1位になった割合"); ax.legend(frameon=False, ncol=3, loc="lower center", bbox_to_anchor=(.5, 1.0))
save(fig, "a787_top_share.png", SRC)

# 図3：x1 の標準偏差を変えたときの x1 の順位
fig, ax = plt.subplots(figsize=(8.5, 4.4))
ax.plot(W.sd_x1, W.rank_std_x1, "o-", color=ORANGE, label="標準化係数での x1 の順位")
ax.plot(W.sd_x1, W.rank_raw_x1, "o-", color=BLUE, label="ふつうの係数での x1 の順位")
ax.set_xscale("log", base=2); ax.set_xticks(W.sd_x1); ax.set_xticklabels([f"{v:g}" for v in W.sd_x1])
ax.set_yticks([1, 2, 3]); ax.invert_yaxis(); ax.set_xlabel("x1 の標準偏差（x2・x3 は1）"); ax.set_ylabel("順位（平均）")
ax.legend(frameon=False); ax.set_title("x1 の効き方は変えていないのに、ばらつきが大きいだけで標準化係数では1位になる")
save(fig, "a787_sweep.png", SRC)
print(json.dumps({k: v for k, v in out.items() if k != "sweep"}, indent=1)); print(W.round(3))

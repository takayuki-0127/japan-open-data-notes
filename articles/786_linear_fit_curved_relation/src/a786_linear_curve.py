"""786 曲がった関係に直線を当てはめると、「効果」はどの範囲で大きく、どの範囲で小さく読まれるのか

架空のデータ。x は 0〜10 の一様分布、y = 10·log(1+k·x)/log(1+10k) + ばらつき（sd 1）。
k が大きいほど、x の小さいところで急に上がり、大きいところで平らになる（k→0 で直線）。
件数200で各500回、直線・2次の項つき・3区間の直線を当てはめ、
x=1・5・9 での「x が1増えると y がいくつ増えるか」を本当の傾きと比べる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GRAY, GREEN, LIGHT

SRC = "出典：架空のデータ（作成者が乱数で作成、seed 786）"
rng = np.random.default_rng(786)
N, R = 200, 500
KS = [0.01, 0.1, 0.3, 1.0, 3.0]
XS = [1, 5, 9]


def f(x, k): return 10 * np.log1p(k * x) / np.log1p(10 * k)
def df(x, k): return 10 * k / ((1 + k * x) * np.log1p(10 * k))


def fits(x, y):
    b_lin = np.polyfit(x, y, 1)[0]
    c2, c1, _ = np.polyfit(x, y, 2)
    quad = {x0: c1 + 2 * c2 * x0 for x0 in XS}
    pw = {}
    for x0, (lo, hi) in zip(XS, [(0, 10 / 3), (10 / 3, 20 / 3), (20 / 3, 10)]):
        m = (x >= lo) & (x < hi); pw[x0] = np.polyfit(x[m], y[m], 1)[0]
    return b_lin, quad, pw


rows = []
for k in KS:
    acc = {"lin": [], **{f"quad{x0}": [] for x0 in XS}, **{f"pw{x0}": [] for x0 in XS}}
    for _ in range(R):
        x = rng.uniform(0, 10, N); y = f(x, k) + rng.normal(0, 1, N)
        b, q, p = fits(x, y)
        acc["lin"].append(b)
        for x0 in XS: acc[f"quad{x0}"].append(q[x0]); acc[f"pw{x0}"].append(p[x0])
    for x0 in XS:
        rows.append(dict(k=k, x=x0, true=df(x0, k), linear=np.mean(acc["lin"]), quad=np.mean(acc[f"quad{x0}"]),
                         piecewise=np.mean(acc[f"pw{x0}"]), linear_sd=np.std(acc["lin"]),
                         quad_sd=np.std(acc[f"quad{x0}"]), pw_sd=np.std(acc[f"pw{x0}"])))
S = pd.DataFrame(rows); S.to_csv(RES / "summary.csv", index=False)

g = lambda k, x0, c: float(S[(S.k == k) & (S.x == x0)][c].iloc[0])
out = {"n": N, "reps": R, "ks": KS,
       "by_k": {str(k): {str(x0): {c: round(g(k, x0, c), 3) for c in ["true", "linear", "quad", "piecewise"]} for x0 in XS} for k in KS},
       "k1_true_x1": g(1.0, 1, "true"), "k1_true_x9": g(1.0, 9, "true"), "k1_linear": g(1.0, 1, "linear"),
       "k1_ratio_x1": g(1.0, 1, "true") / g(1.0, 1, "linear"), "k1_ratio_x9": g(1.0, 9, "linear") / g(1.0, 9, "true"),
       "k1_quad_x1": g(1.0, 1, "quad"), "k1_quad_x9": g(1.0, 9, "quad"),
       "k3_true_x1": g(3.0, 1, "true"), "k3_true_x9": g(3.0, 9, "true"), "k3_linear": g(3.0, 1, "linear"),
       "k3_quad_x1": g(3.0, 1, "quad"), "k3_pw_x1": g(3.0, 1, "piecewise"),
       "k001_linear": g(0.01, 1, "linear"), "k001_true_x1": g(0.01, 1, "true"),
       "linear_sd_k1": g(1.0, 1, "linear_sd"), "pw_sd_k1_x1": g(1.0, 1, "pw_sd")}
json.dump(out, open(RES / "a786_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：例（k=1）
k = 1.0; x = rng.uniform(0, 10, N); y = f(x, k) + rng.normal(0, 1, N)
fig, ax = plt.subplots(figsize=(8.5, 4.8))
ax.scatter(x, y, s=10, color=LIGHT)
xx = np.linspace(0, 10, 200); ax.plot(xx, f(xx, k), color=INK if False else "#0b0b0b", lw=2, label="本当の関係")
b, a = np.polyfit(x, y, 1); ax.plot(xx, a + b * xx, color=ORANGE, lw=2, label=f"直線（傾き {b:.2f}）")
for x0 in [1, 9]:
    t = df(x0, k); ax.plot([x0 - 1, x0 + 1], [f(x0, k) - t, f(x0, k) + t], color=BLUE, lw=3)
    ax.text(x0, f(x0, k) + t + .6, f"x={x0} の本当の傾き {t:.2f}", ha="center", fontsize=9, color=BLUE)
ax.set_xlabel("x"); ax.set_ylabel("y"); ax.legend(frameon=False, loc="lower right")
ax.set_title("直線の傾きは1つだけ。x の小さい所の効き目は小さく、大きい所は大きく読まれる")
save(fig, "a786_example.png", SRC)

# 図2：k=1 での3つの当てはめ
fig, ax = plt.subplots(figsize=(8.5, 4.6)); s = S[S.k == 1.0]; w = .2; xi = np.arange(3)
for j, (c, col, lab) in enumerate([("true", "#0b0b0b", "本当の傾き"), ("linear", ORANGE, "直線"), ("quad", BLUE, "2次の項つき"), ("piecewise", GREEN, "3区間の直線")]):
    ax.bar(xi + (j - 1.5) * w, s[c], w, color=col, label=lab)
ax.set_xticks(xi); ax.set_xticklabels([f"x={v}" for v in XS]); ax.set_ylabel("x が1増えたときの y の増え方")
ax.legend(frameon=False); ax.set_title("曲がり k=1：直線は x=1 の効き目を半分以下に、x=9 を2倍以上に読む（500回の平均）")
save(fig, "a786_three_fits.png", SRC)

# 図3：曲がり方ごとの、直線の傾き ÷ 本当の傾き
fig, ax = plt.subplots(figsize=(8.5, 4.6))
for x0, col in zip(XS, [BLUE, GRAY, ORANGE]):
    s = S[S.x == x0]; ax.plot(range(len(KS)), s.linear / s.true, "o-", color=col, label=f"x={x0}")
ax.axhline(1, color=GRAY, lw=.8, ls="--"); ax.set_yscale("log")
ax.set_xticks(range(len(KS))); ax.set_xticklabels([f"k={v}" for v in KS]); ax.set_xlabel("曲がり方（k が小さいほど直線に近い）")
ax.set_ylabel("直線の傾き ÷ 本当の傾き（対数）"); ax.legend(frameon=False)
ax.set_title("曲がるほど、x の小さい所は小さく、大きい所は大きく読まれる")
save(fig, "a786_by_k.png", SRC)
print(json.dumps({k: v for k, v in out.items() if k != "by_k"}, indent=1))

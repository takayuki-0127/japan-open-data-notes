"""720 2つの系列が同じ原因で動き、片方が遅れて反応するとき、グレンジャー因果の検定は何%で「因果あり」と言うのか

架空の月次の系列。共通の原因 Z（AR(1)、係数0.5）があり、
  X_t ＝ Z_t ＋ ノイズ（標準偏差 σx）
  Y_t ＝ b×Z_{t−L} ＋ ノイズ（標準偏差1）、b＝0.3（基本）
X と Y の間に直接の関係はない（X を動かしても Y は動かない）。
検定：「X の過去が Y の予測に役立つか」（グレンジャー因果、ずらし4か月、F 検定、5%）
  ふつうの検定：Y の過去4か月 ＋ X の過去4か月
  共通の原因を入れた検定：さらに Z の過去4か月を入れる
遅れ L＝0〜4か月（長さ120・b＝0.3）、系列の長さ 60・120・240か月、Z の効き b＝0.1・0.2・0.3・0.5 を変えて、各500回。X のノイズは σx＝1。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
from common import RES, save, BLUE, ORANGE, GRAY, LIGHT, INK, GREEN

SRC = "出典：架空の月次の系列（作成者が乱数で作成、seed 720）"
rng = np.random.default_rng(720)
P = 4


def make(n, L, b, sx=1.0, burn=50):
    m = n + burn + L
    z = np.zeros(m); e = rng.normal(0, 1, m)
    for t in range(1, m): z[t] = 0.5 * z[t - 1] + e[t]
    x = z + rng.normal(0, sx, m)
    y = b * np.r_[np.zeros(L), z[:m - L]] + rng.normal(0, 1, m)
    return x[-n:], y[-n:], z[-n:]


def lagmat(v, p):
    return np.column_stack([v[p - k - 1:len(v) - k - 1] for k in range(p)])


def ftest(y, base, extra):
    Y = y[P:]; X0 = np.column_stack([np.ones(len(Y))] + base); X1 = np.column_stack([X0] + extra)
    r0 = Y - X0 @ np.linalg.lstsq(X0, Y, rcond=None)[0]; r1 = Y - X1 @ np.linalg.lstsq(X1, Y, rcond=None)[0]
    q = X1.shape[1] - X0.shape[1]; df = len(Y) - X1.shape[1]
    F = ((r0 @ r0 - r1 @ r1) / q) / (r1 @ r1 / df)
    return float(stats.f.sf(F, q, df))


def tests(x, y, z):
    ly, lx, lz = lagmat(y, P), lagmat(x, P), lagmat(z, P)
    p_naive = ftest(y, [ly], [lx]); p_ctrl = ftest(y, [ly, lz], [lx])
    p_rev = ftest(x, [lagmat(x, P)], [ly])            # 逆向き：Y の過去が X に役立つか
    return p_naive, p_ctrl, p_rev


REPS = 500
rows = []
SET = [(L, 120, 0.3) for L in range(5)] + [(2, n, 0.3) for n in (60, 240)] + [(2, 120, b) for b in (0.1, 0.2, 0.5)]
for L, n, b in SET:
    for r in range(REPS):
        a1, a2, a3 = tests(*make(n, L, b))
        rows.append({"lag": L, "n": n, "b": b, "naive": a1 < 0.05, "ctrl": a2 < 0.05, "reverse": a3 < 0.05})
R = pd.DataFrame(rows)
S = R.groupby(["lag", "n", "b"])[["naive", "ctrl", "reverse"]].mean().mul(100).reset_index()
S.round(1).to_csv(RES / "summary.csv", index=False)
base = S[(S.n == 120) & (S.b == 0.3)].set_index("lag")
byn = S[(S.lag == 2) & (S.b == 0.3)].sort_values("n"); byb = S[(S.lag == 2) & (S.n == 120)].sort_values("b")

out = {"reps": REPS, "test_lags": P, "alpha": 0.05, "z_ar": 0.5, "x_noise_sd": 1.0, "b_base": 0.3,
       "n120_b03": {str(L): {"naive_pct": round(float(base.loc[L, "naive"]), 1), "ctrl_pct": round(float(base.loc[L, "ctrl"]), 1),
                             "reverse_pct": round(float(base.loc[L, "reverse"]), 1)} for L in base.index},
       "lag2_by_n": {str(int(r.n)): round(float(r.naive), 1) for r in byn.itertuples()},
       "lag2_by_b_n120": {str(r.b): round(float(r.naive), 1) for r in byb.itertuples()},
       "lag2_by_b_ctrl": {str(r.b): round(float(r.ctrl), 1) for r in byb.itertuples()}}
json.dump(out, open(RES / "a720_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：例
x, y, z = make(120, 2, 1.0)  # 図では見やすいよう b＝1
fig, ax = plt.subplots(figsize=(9, 3.6)); t = np.arange(120)
ax.plot(t, z, color=GRAY, lw=1, label="共通の原因 Z（ふつうは見えない）")
ax.plot(t, x + 4, color=BLUE, lw=1, label="X ＝ Z ＋ ノイズ（上に4ずらして表示）")
ax.plot(t, y - 4, color=ORANGE, lw=1, label="Y ＝ 2か月前の Z ＋ ノイズ（図では b＝1、下に4ずらして表示）")
ax.set_xlabel("月"); ax.set_yticks([]); ax.set_ylim((y - 4).min() - 0.5, (x + 4).max() + 4.5); ax.legend(frameon=False, fontsize=8.5, loc="upper left", ncol=1)
ax.set_title("X と Y は直接つながっていない。どちらも Z で動き、Y は2か月遅れる")
save(fig, "a720_example.png", SRC)

# 図2：遅れごとの「因果あり」の割合
fig, ax = plt.subplots(figsize=(8, 3.8)); xs = np.arange(5); wd = 0.27
for dx, col, c, lab in [(-wd, ORANGE, "naive", "X→Y（ふつうの検定）"), (0, BLUE, "ctrl", "X→Y（Z の過去を入れた検定）"), (wd, GRAY, "reverse", "Y→X（逆向き）")]:
    v = base[c].values; ax.bar(xs + dx, v, wd, color=col, label=lab)
    for i in range(5): ax.text(xs[i] + dx, v[i] + 1.5, f"{v[i]:.0f}", ha="center", fontsize=8)
ax.axhline(5, color=INK, lw=0.8, ls="--"); ax.text(4.45, 6.5, "5%", fontsize=8)
ax.set_xticks(xs); ax.set_xticklabels([f"{L}か月" for L in range(5)]); ax.set_xlabel("Y が Z に反応する遅れ")
ax.set_ylabel("「因果あり」とした割合（%）"); ax.set_ylim(0, 80); ax.legend(frameon=False, fontsize=8.5, loc="upper left", ncol=3)
ax.set_title(f"直接の関係がなくても、遅れがあると約半分で X→Y が「因果あり」（120か月・b＝0.3、{REPS}回）", fontsize=12)
save(fig, "a720_by_lag.png", SRC)

# 図3：系列の長さと Z の効き（遅れ2か月）
fig, axes = plt.subplots(1, 2, figsize=(10, 3.6), sharey=True)
axes[0].bar([str(int(v)) for v in byn.n], byn.naive, color=ORANGE)
for i, v in enumerate(byn.naive): axes[0].text(i, v + 1.5, f"{v:.0f}%", ha="center", fontsize=9)
axes[0].set_xlabel("系列の長さ（か月）、b＝0.3"); axes[0].set_ylabel("X→Y の「因果あり」（%）"); axes[0].set_title("長いほど「因果あり」が増える")
axes[1].bar([str(v) for v in byb.b], byb.naive, color=ORANGE)
for i, v in enumerate(byb.naive): axes[1].text(i, v + 1.5, f"{v:.0f}%", ha="center", fontsize=9)
axes[1].set_xlabel("Y に対する Z の効き b、長さ120か月"); axes[1].set_title("Z の効きが強いほど増える")
axes[0].set_ylim(0, 110)
fig.suptitle("遅れ2か月・ふつうの検定（ずらし4か月）", y=1.02)
save(fig, "a720_n_strength.png", SRC)
print(json.dumps(out, ensure_ascii=False))

"""750 交互作用を入れた回帰で、変数を中心化しないと、主効果の係数はどう読めてしまうのか

架空の店400店。施策 z（0/1、無作為に半分）、店の広さ x（平均 μ、標準偏差20）。
売上の伸び y = 5×z + 0.1×(x−μ) + γ×z×(x−μ) + 誤差（sd 15）
つまり、広さが平均の店での施策の効果は5（どの μ・γ でも同じ）、施策の効果は広さ1あたり γ ずつ変わる。
y ~ z + x + z×x を、x をそのまま入れる場合と、平均を引いて（中心化して）入れる場合で当てはめ、z の係数（主効果）と p 値を比べる。
γ＝0.2 で μ＝0・25・50・100・200、μ＝100 で γ＝0〜0.3。各1,000回。
"""
import json
import numpy as np
import pandas as pd
from scipy import stats
import matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GRAY, GREEN, LIGHT

SRC = "出典：架空のデータ（作成者が乱数で作成、seed 750）"
rng = np.random.default_rng(750)
N, R = 400, 1000


def fit(y, z, x):
    X = np.column_stack([np.ones(len(y)), z, x, z * x])
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    e = y - X @ b; df = len(y) - 4; s2 = e @ e / df
    se = np.sqrt(np.diag(s2 * np.linalg.inv(X.T @ X)))
    return b, 2 * stats.t.sf(np.abs(b / se), df), se


def sim(mu, gam):
    z = (rng.random(N) < .5).astype(float); x = mu + 20 * rng.standard_normal(N)
    y = 5 * z + .1 * (x - mu) + gam * z * (x - mu) + 15 * rng.standard_normal(N)
    b_raw, p_raw, _ = fit(y, z, x)
    b_c, p_c, _ = fit(y, z, x - x.mean())
    return b_raw[1], p_raw[1], b_c[1], p_c[1], b_raw[3], b_c[3]


rows = []
for mu in [0, 25, 50, 100, 200]:
    v = np.array([sim(mu, .2) for _ in range(R)])
    rows.append(dict(mu=mu, gamma=.2, z_raw=v[:, 0].mean(), z_raw_sig_pos=np.mean((v[:, 1] < .05) & (v[:, 0] > 0)), z_raw_sig_neg=np.mean((v[:, 1] < .05) & (v[:, 0] < 0)),
                     z_c=v[:, 2].mean(), z_c_sig_pos=np.mean((v[:, 3] < .05) & (v[:, 2] > 0)), z_c_sig_neg=np.mean((v[:, 3] < .05) & (v[:, 2] < 0)),
                     inter_raw=v[:, 4].mean(), inter_c=v[:, 5].mean(), theory_raw=5 - .2 * mu))
A = pd.DataFrame(rows); A.to_csv(RES / "by_mu.csv", index=False)
rows = []
for gam in [0, .05, .1, .2, .3]:
    v = np.array([sim(100, gam) for _ in range(R)])
    rows.append(dict(mu=100, gamma=gam, z_raw=v[:, 0].mean(), z_raw_sig_pos=np.mean((v[:, 1] < .05) & (v[:, 0] > 0)), z_raw_sig_neg=np.mean((v[:, 1] < .05) & (v[:, 0] < 0)),
                     z_c=v[:, 2].mean(), z_c_sig_pos=np.mean((v[:, 3] < .05) & (v[:, 2] > 0)), z_c_sig_neg=np.mean((v[:, 3] < .05) & (v[:, 2] < 0)), theory_raw=5 - gam * 100))
G = pd.DataFrame(rows); G.to_csv(RES / "by_gamma.csv", index=False)
a = lambda mu, c: float(A[A.mu == mu][c].iloc[0]); g = lambda gm, c: float(G[np.isclose(G.gamma, gm)][c].iloc[0])
out = {"stores": N, "reps": R, "effect_at_mean": 5,
       "mu100_g02": {"z_raw": a(100, "z_raw"), "z_raw_sig_neg": a(100, "z_raw_sig_neg"), "z_c": a(100, "z_c"), "z_c_sig_pos": a(100, "z_c_sig_pos"),
                     "interaction_raw": a(100, "inter_raw"), "interaction_c": a(100, "inter_c")},
       "by_mu_z_raw": {int(m): round(a(m, "z_raw"), 2) for m in A.mu}, "by_mu_z_c": {int(m): round(a(m, "z_c"), 2) for m in A.mu},
       "by_gamma_z_raw": {f"{gm:.2f}": round(g(gm, "z_raw"), 2) for gm in G.gamma},
       "by_gamma_raw_sig_neg": {f"{gm:.2f}": g(gm, "z_raw_sig_neg") for gm in G.gamma},
       "by_gamma_raw_sig_pos": {f"{gm:.2f}": g(gm, "z_raw_sig_pos") for gm in G.gamma},
       "by_gamma_c_sig_pos": {f"{gm:.2f}": g(gm, "z_c_sig_pos") for gm in G.gamma},
       "mu25_g02_z_raw": a(25, "z_raw"), "mu25_g02_raw_sig_pos": a(25, "z_raw_sig_pos"), "mu25_g02_raw_sig_neg": a(25, "z_raw_sig_neg")}
json.dump(out, open(RES / "a750_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：1回分の当てはめと、x=0 までの線
z = (rng.random(N) < .5).astype(float); x = 100 + 20 * rng.standard_normal(N)
y = 5 * z + .1 * (x - 100) + .2 * z * (x - 100) + 15 * rng.standard_normal(N)
b, _, _ = fit(y, z, x)
fig, ax = plt.subplots(figsize=(9, 4.6)); xs = np.linspace(0, 160, 100)
ax.scatter(x[z == 0], y[z == 0], s=6, color=LIGHT, label="施策なしの店"); ax.scatter(x[z == 1], y[z == 1], s=6, color="#f2b49b", label="施策ありの店")
ax.plot(xs, b[0] + b[2] * xs, color=BLUE, lw=2); ax.plot(xs, b[0] + b[1] + (b[2] + b[3]) * xs, color=ORANGE, lw=2)
ax.axvline(0, color=GRAY, lw=1); ax.axvline(100, color=GRAY, ls=":", lw=1)
ax.annotate(f"広さ0での差＝z の係数 {b[1]:.1f}", xy=(0, b[0] + b[1] / 2), xytext=(8, -25), fontsize=9, color=ORANGE)
ax.annotate(f"広さの平均（100）での差 ≒ {b[1] + b[3] * 100:.1f}", xy=(100, 0), xytext=(103, 22), fontsize=9, color=ORANGE)
ax.set_xlabel("店の広さ x（平均100）"); ax.set_ylabel("売上の伸び"); ax.legend(frameon=False, loc="upper left")
ax.set_title("中心化しないと、z の係数は「広さ0の店」での差になる（データのない所）")
save(fig, "a750_lines.png", SRC)

# 図2：平均 μ と z の係数
fig, ax = plt.subplots(figsize=(9, 4.6))
ax.plot(A.mu, A.z_raw, "o-", color=ORANGE, label="中心化しない")
ax.plot(A.mu, A.z_c, "o-", color=BLUE, label="中心化する")
for m, v in zip(A.mu, A.z_raw):
    ax.text(m, v - 3, f"{v:.1f}", ha="center", fontsize=9, color=ORANGE)
ax.axhline(5, color=GRAY, ls="--", lw=1); ax.text(140, 6.5, "広さが平均の店での効果 5", color=GRAY, fontsize=9)
ax.axhline(0, color=GRAY, lw=.8)
ax.set_xlabel("店の広さの平均 μ（交互作用 γ＝0.2）"); ax.set_ylabel("z の係数（1,000回の平均）"); ax.legend(frameon=False, loc="lower left")
ax.set_title("同じ効果でも、x の平均が0から離れるほど、中心化しない係数は動く")
save(fig, "a750_by_mu.png", SRC)

# 図3：交互作用の強さと「有意」の向き
fig, ax = plt.subplots(figsize=(9, 4.6)); xx = np.arange(len(G)); w = .27
ax.bar(xx - w, G.z_raw_sig_neg * 100, w, color=ORANGE, label="中心化しない：有意にマイナス")
ax.bar(xx, G.z_raw_sig_pos * 100, w, color="#f2b49b", label="中心化しない：有意にプラス")
ax.bar(xx + w, G.z_c_sig_pos * 100, w, color=BLUE, label="中心化する：有意にプラス")
ax.set_xticks(xx); ax.set_xticklabels([f"γ＝{gm:g}" for gm in G.gamma]); ax.set_xlabel("交互作用の強さ（広さの平均 μ＝100）")
ax.set_ylabel("z の係数が有意になった割合（%）"); ax.legend(frameon=False, fontsize=9, loc="upper left"); ax.set_ylim(0, 115)
ax.set_title("中心化しないと、効果がプラスの施策が「有意にマイナス」と読める")
save(fig, "a750_sign.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))

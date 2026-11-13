"""626 2つの事業の損害を「独立」と置いて合わせると、合計の99.5%点はどれだけ小さく出るのか

架空の2つの事業の年間の損害。事業1：対数正規（平均100、変動係数0.3）、事業2：対数正規（平均100、変動係数0.6）。
2つのつながりは正規コピュラ（相関 ρ = 0・0.25・0.5・0.75）で入れる（これを「本当」とする）。合計の99.5%点を4通りで出す：
  T 本当（コピュラでシミュレーション）、I 独立と置いてシミュレーション、
  M 相関行列の式（それぞれの「99.5%点−平均」を √(a²+b²+2ρab) で合わせて平均に足す）、S 単純に足す（99.5%点の和）
同じことを、同じ形の事業を5つ合わせる場合でも行う。各200万回。数字は置いた分布で決まる。料率・備金・資本の助言ではない。
"""
import json
import numpy as np
import pandas as pd
from scipy import stats
import matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GRAY, GREEN, LIGHT, INK

SRC = "出典：架空の年間の損害（作成者が乱数で作成、seed 626）"
rng = np.random.default_rng(626)
NSIM, Q = 2_000_000, 0.995
RHOS = [0.0, 0.25, 0.5, 0.75]


def ln_params(mean, cv):
    s2 = np.log(1 + cv ** 2)
    return np.log(mean) - s2 / 2, np.sqrt(s2)


LINES2 = [(100, 0.3), (100, 0.6)]


def simulate(lines, rho, rng):
    k = len(lines)
    C = np.full((k, k), rho); np.fill_diagonal(C, 1)
    z = rng.standard_normal((NSIM, k)) @ np.linalg.cholesky(C).T
    x = np.column_stack([np.exp(m + s * z[:, j]) for j, (m, s) in enumerate(ln_params(a, b) for a, b in lines)])
    return x


def standalone(lines):
    q = []
    for a, b in lines:
        m, s = ln_params(a, b)
        q.append(float(np.exp(m + s * stats.norm.ppf(Q))))
    return np.array(q)


def run(lines):
    qs = standalone(lines); means = np.array([a for a, b in lines]); exc = qs - means
    ind = simulate(lines, 0.0, rng).sum(1)
    q_ind = float(np.quantile(ind, Q))
    rows = []
    for rho in RHOS:
        tot = simulate(lines, rho, rng).sum(1)
        q_true = float(np.quantile(tot, Q))
        k = len(lines); C = np.full((k, k), rho); np.fill_diagonal(C, 1)
        q_mat = float(means.sum() + np.sqrt(exc @ C @ exc))
        rows.append({"rho": rho, "true": q_true, "indep": q_ind, "matrix": q_mat, "simple_sum": float(qs.sum()),
                     "mean_total": float(means.sum()),
                     "indep_vs_true_pct": 100 * (q_ind / q_true - 1), "matrix_vs_true_pct": 100 * (q_mat / q_true - 1),
                     "sum_vs_true_pct": 100 * (qs.sum() / q_true - 1),
                     "cap_true": q_true - means.sum(), "cap_indep": q_ind - means.sum()})
    return pd.DataFrame(rows), qs


T2, qs2 = run(LINES2)
LINES5 = [(100, 0.3), (100, 0.4), (100, 0.5), (100, 0.6), (100, 0.7)]
T5, qs5 = run(LINES5)
T2.round(3).to_csv(RES / "two_lines.csv", index=False); T5.round(3).to_csv(RES / "five_lines.csv", index=False)
pd.concat([T2.assign(lines=2), T5.assign(lines=5)]).round(3).to_csv(RES / "summary.csv", index=False)
# 裾の様子（2事業、ρ=0 と 0.5）
tails = {}
for rho in [0.0, 0.5]:
    tot = simulate(LINES2, rho, np.random.default_rng(6260)).sum(1)
    xs = np.linspace(200, 600, 81)
    tails[rho] = (xs, np.array([(tot > x).mean() for x in xs]))
pd.DataFrame({"x": tails[0][0], "exceed_rho0": tails[0][1], "exceed_rho0.5": tails[0.5][1]}).to_csv(RES / "tail_two_lines.csv", index=False)
out = {"nsim": NSIM, "q": Q, "lines2": LINES2, "standalone_q_2": qs2.round(2).tolist(), "two_lines": T2.round(3).to_dict(orient="records"),
       "lines5": LINES5, "standalone_q_5": qs5.round(2).tolist(), "five_lines": T5.round(3).to_dict(orient="records")}
json.dump(out, open(RES / "a626_main.json", "w"), ensure_ascii=False, indent=1)

# 図1
fig, ax = plt.subplots(figsize=(8.5, 4.2))
ax.plot(T2.rho, T2.true, marker="o", color=INK, label="本当（相関を入れたシミュレーション）")
ax.plot(T2.rho, T2.indep, marker="s", color=ORANGE, label="独立と置いたシミュレーション")
ax.plot(T2.rho, T2.matrix, marker="^", color=BLUE, label="相関行列の式")
ax.plot(T2.rho, T2.simple_sum, ls="--", color=GRAY, label="それぞれの99.5%点を足す")
for r, v in zip(T2.rho, T2.true):
    ax.text(r, v + 4, f"{v:.0f}", ha="center", fontsize=8.5)
ax.set_xlabel("2つの事業の相関 ρ"); ax.set_ylabel("合計の99.5%点"); ax.set_xticks(RHOS)
ax.set_title("2つの事業の合計の99.5%点（平均の合計は200）"); ax.legend(frameon=False, fontsize=9)
save(fig, "a626_q995_two_lines.png", SRC)

# 図2：独立と置いたときの過小（平均を引いた部分で）
fig, ax = plt.subplots(figsize=(8.5, 4))
w = 0.35; xs = np.arange(len(RHOS))
for j, (T, lab, c) in enumerate([(T2, "2つの事業", BLUE), (T5, "5つの事業", ORANGE)]):
    v = 100 * (T.cap_indep / T.cap_true - 1)
    ax.bar(xs + (j - 0.5) * w, v, w, color=c, label=lab)
    for x, vv in zip(xs + (j - 0.5) * w, v):
        ax.text(x, vv - 1.5 if vv < 0 else vv + 0.5, f"{vv:.0f}%", ha="center", fontsize=8.5, va="top" if vv < 0 else "bottom")
ax.axhline(0, color=GRAY, lw=0.8); ax.set_xticks(xs); ax.set_xticklabels([f"ρ={r}" for r in RHOS])
ax.set_ylabel("独立と置いた値の、本当との差（%）"); ax.legend(frameon=False, fontsize=9)
ax.set_title("「99.5%点−平均」は、相関があるほど独立の仮定で小さく出る")
save(fig, "a626_underestimate.png", SRC)

# 図3：裾
fig, ax = plt.subplots(figsize=(8.5, 4))
ax.plot(tails[0][0], tails[0][1], color=ORANGE, label="相関 0")
ax.plot(tails[0.5][0], tails[0.5][1], color=BLUE, label="相関 0.5")
ax.axhline(1 - Q, color=GRAY, ls=":", label="0.5%（200年に1度）")
ax.set_yscale("log"); ax.set_xlabel("合計の損害"); ax.set_ylabel("これを超える確率（対数目盛）"); ax.legend(frameon=False, fontsize=9)
ax.set_title("2つの事業の合計が大きな値を超える確率")
save(fig, "a626_tail.png", SRC)
print(T2.round(2).to_string()); print(T5.round(2).to_string()); print(qs2, qs5)

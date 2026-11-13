"""519 100万件のデータでは、相関0.01のような小さな関係でも何%の回で「有意」と出るのか（統計の考え方）

架空のデータ。x と y は平均0・標準偏差1の正規分布で、本当の相関は ρ = 0・0.005・0.01・0.02・0.05。
件数 n = 100〜100万。相関係数の検定（両側5%）で「有意」と出る割合を、
(1) フィッシャーの z 変換の近似式、(2) 標本の相関を直接作るシミュレーション（ウィシャート分布、各20,000回）、
(3) n=10万・ρ=0.01 では生データを作るシミュレーション（500回）で数える。
"""
import json
import numpy as np, pandas as pd
from scipy import stats
import matplotlib.pyplot as plt
from common import FIG, RES, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 519
SRC = "架空のデータ（作成者が乱数で作成、seed 519）"
RHOS = [0, 0.005, 0.01, 0.02, 0.05]
NS = [100, 300, 1000, 3000, 10_000, 30_000, 100_000, 300_000, 1_000_000]
ZC = stats.norm.ppf(0.975)


def power_z(rho, n):
    m = np.arctanh(rho); se = 1 / np.sqrt(n - 3)
    return float(stats.norm.sf(ZC - m / se) + stats.norm.cdf(-ZC - m / se))


def sim_r(rho, n, reps, rng):
    S = stats.wishart.rvs(df=n - 1, scale=np.array([[1, rho], [rho, 1]]), size=reps, random_state=rng)
    return S[:, 0, 1] / np.sqrt(S[:, 0, 0] * S[:, 1, 1])


def sig_t(r, n):
    t = r * np.sqrt((n - 2) / (1 - r ** 2))
    return 2 * stats.t.sf(np.abs(t), n - 2) < 0.05


def main():
    rng = np.random.default_rng(SEED)
    rows = []
    for rho in RHOS:
        for n in NS:
            r = sim_r(rho, n, 20_000, rng)
            ci_w = float(np.tanh(np.arctanh(rho) + ZC / np.sqrt(n - 3)) - np.tanh(np.arctanh(rho) - ZC / np.sqrt(n - 3)))
            rows.append(dict(rho=rho, n=n, power_formula=round(power_z(rho, n), 4), power_sim=round(float(sig_t(r, n).mean()), 4),
                             ci95_width=round(ci_w, 5), r2_true_pct=round(rho ** 2 * 100, 4), median_abs_r=round(float(np.median(np.abs(r))), 5)))
    df = pd.DataFrame(rows); df.to_csv(RES / "power_grid.csv", index=False)
    # 80%の回で有意になる件数
    need = {str(rho): int(np.ceil(((ZC + stats.norm.ppf(0.8)) / np.arctanh(rho)) ** 2 + 3)) for rho in RHOS if rho > 0}
    # 生データでの確認（n=10万、ρ=0.01、500回）
    r_raw = []
    for _ in range(500):
        x = rng.standard_normal(100_000); y = 0.01 * x + np.sqrt(1 - 0.01 ** 2) * rng.standard_normal(100_000)
        r_raw.append(np.corrcoef(x, y)[0, 1])
    r_raw = np.array(r_raw); raw_rate = float(sig_t(r_raw, 100_000).mean())
    # 100万件・ρ=0.01 の1回分：x の十分位ごとの y の平均
    n = 1_000_000; x = rng.standard_normal(n); y = 0.01 * x + np.sqrt(1 - 0.01 ** 2) * rng.standard_normal(n)
    r1 = float(np.corrcoef(x, y)[0, 1]); p1 = float(2 * stats.t.sf(abs(r1) * np.sqrt((n - 2) / (1 - r1 ** 2)), n - 2))
    dec = pd.qcut(x, 10, labels=False); dm = pd.DataFrame(dict(d=dec, y=y)).groupby("d").y.agg(["mean", "std"])
    dm.round(5).to_csv(RES / "decile_one_run.csv")
    g = lambda rho, n, c: float(df[(df.rho == rho) & (df.n == n)][c].iloc[0])
    out = dict(seed=SEED, alpha=0.05, reps=20000, n_for_80pct_power=need,
               raw_check_n100000_rho001=dict(reps=500, sig_rate=round(raw_rate, 4), formula=round(power_z(0.01, 100_000), 4)),
               one_run_n1e6_rho001=dict(r=round(r1, 5), p=float(f"{p1:.3g}"), r2_pct=round(r1 ** 2 * 100, 4),
                                        decile_mean_low=round(float(dm["mean"].iloc[0]), 4), decile_mean_high=round(float(dm["mean"].iloc[-1]), 4),
                                        decile_sd=round(float(dm["std"].mean()), 4)),
               key={f"rho{rho}_n{n}": dict(power_sim=g(rho, n, "power_sim"), power_formula=g(rho, n, "power_formula"), ci95_width=g(rho, n, "ci95_width"))
                    for rho in [0, 0.005, 0.01, 0.02] for n in [1000, 10_000, 100_000, 1_000_000]})
    json.dump(out, open(RES / "a519_main.json", "w"), ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "key"}, ensure_ascii=False, indent=0))
    print(df.pivot(index="n", columns="rho", values="power_sim"))

    # 図1：有意になる割合
    fig, ax = plt.subplots(figsize=(7.6, 4.4)); cols = [GRAY, LIGHT, BLUE, ORANGE, INK]
    for rho, c in zip(RHOS, cols):
        x_ = df[df.rho == rho]; ax.plot(x_.n, x_.power_sim * 100, "o-", color=c, lw=2.2, ms=5, label=f"本当の相関 {rho:g}")
    ax.set_xscale("log"); ax.set_xlabel("件数（対数）"); ax.set_ylabel("「有意」と出た割合（%）"); ax.set_ylim(0, 102)
    ax.set_xticks(NS[::2], ["100", "1,000", "1万", "10万", "100万"])
    ax.set_title("件数が100万件あると、相関0.01でもほぼ毎回「有意」と出る")
    ax.legend(frameon=False, fontsize=9, loc="center left")
    save(fig, "a519_power.png", SRC + "。両側5%の検定、各20,000回")

    # 図2：信頼区間の幅と R²
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    x_ = df[df.rho == 0.01]
    ax.plot(x_.n, x_.ci95_width, "o-", color=BLUE, lw=2.2, label="相関の95%信頼区間の幅")
    ax.axhline(0.01, color=ORANGE, ls="--", lw=1.4); ax.text(130, 0.0115, "相関0.01の大きさ", color=ORANGE, fontsize=9)
    ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlabel("件数（対数）"); ax.set_ylabel("幅（対数）")
    ax.set_xticks(NS[::2], ["100", "1,000", "1万", "10万", "100万"])
    ax.set_title("件数が増えると区間は狭くなるが、相関0.01で説明できる分散は0.01%のまま")
    ax.legend(frameon=False, fontsize=9)
    save(fig, "a519_ci_width.png", SRC + "。本当の相関0.01のときの幅（どの相関でもほぼ同じ）")

    # 図3：100万件の1回分、x の十分位ごとの y の平均
    fig, ax = plt.subplots(figsize=(7.6, 4.4)); xs = np.arange(1, 11)
    ax.bar(xs, dm["mean"], color=BLUE, width=0.6, label="y の平均")
    ax.errorbar(xs, dm["mean"], yerr=dm["std"], fmt="none", ecolor=GRAY, lw=1, capsize=3, label="y の標準偏差（±1）")
    ax.axhline(0, color=INK, lw=0.8); ax.set_xticks(xs, [f"{i}" for i in xs])
    ax.set_xlabel("x の大きさの十分位（1＝いちばん小さい10%）"); ax.set_ylabel("y")
    ax.set_title(f"100万件・相関{r1:.3f}（p = {p1:.1g}）：平均の差は、ばらつきに比べてごくわずか")
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    save(fig, "a519_deciles.png", SRC + "。本当の相関0.01の1回分。各十分位は10万件")


if __name__ == "__main__":
    main()

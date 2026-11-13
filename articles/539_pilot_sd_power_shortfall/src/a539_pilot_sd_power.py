"""539 必要な人数を、過去の小さな調査のばらつきから計算すると、本番で差を見つける力はどれだけ足りなくなるのか（統計・実験計画）

架空の2群の比較（本番は各群 n 人、両側5%の t 検定）。
- 本当の標準偏差 σ = 1、見つけたい差 δ = 0.4（σ の 0.4倍）
- 予備の調査（1群、m 人）で標準偏差 s を見積もり、その s で「検出力80%」の人数 n を決める
  n = ceil( 2 (z_0.975 + z_0.8)^2 s^2 / δ^2 )
- 本番の検出力は、本当の σ のもとで非心 t 分布から計算する
- m = 5・10・20・30・50・100、予備の調査を各 100,000回（乱数の種 539）
- 比べる決め方：(a) s をそのまま使う、(b) s の片側80%の上側信頼限界を使う
確かめとして、m = 20 の一部で本番の t 検定を実際にくり返し、計算の検出力と合うかを見る。
"""
import json
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
from common import FIG, RES, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SRC = "架空の予備の調査と本番の比較（作成者が乱数で作成、seed 539）"
SIGMA, DELTA = 1.0, 0.4
MS = [5, 10, 20, 30, 50, 100]
SIMS = 100_000
ZSUM = stats.norm.ppf(0.975) + stats.norm.ppf(0.8)


def n_for(s):
    return np.maximum(np.ceil(2 * ZSUM ** 2 * s ** 2 / DELTA ** 2), 2).astype(int)


def power(n):
    df = 2 * n - 2
    nc = DELTA / (SIGMA * np.sqrt(2 / n))
    tc = stats.t.ppf(0.975, df)
    pw = 1 - stats.nct.cdf(tc, df, nc) + stats.nct.cdf(-tc, df, nc)
    approx = stats.norm.cdf(nc - stats.norm.ppf(0.975))     # 人数がとても多いときは正規近似（非心 t の計算が数値的に不安定になるため）
    return np.where(np.isfinite(pw), pw, approx)


def main():
    rng = np.random.default_rng(539)
    n_true = int(n_for(np.array([SIGMA]))[0])
    rows, keep = [], {}
    for m in MS:
        s = np.sqrt(SIGMA ** 2 * rng.chisquare(m - 1, SIMS) / (m - 1))
        ucl = s * np.sqrt((m - 1) / stats.chi2.ppf(0.2, m - 1))       # 片側80%の上側信頼限界
        for rule, sv in [("plain", s), ("ucl80", ucl)]:
            n = n_for(sv)
            un, inv = np.unique(n, return_inverse=True)
            pw = power(un)[inv]
            keep[(m, rule)] = pw
            rows.append(dict(m=m, rule=rule, n_median=float(np.median(n)), n_mean=float(n.mean()), n_true=n_true,
                             power_mean=float(pw.mean()), power_median=float(np.median(pw)),
                             power_p10=float(np.quantile(pw, 0.1)), share_below80=float((pw < 0.8).mean()),
                             share_below70=float((pw < 0.7).mean()), share_below50=float((pw < 0.5).mean())))
    sm = pd.DataFrame(rows)
    sm.to_csv(RES / "summary.csv", index=False, float_format="%.6f")

    # 確かめ：m=20 の予備の調査を 400回、それぞれ本番を 500回くり返す
    chk = []
    r2 = np.random.default_rng(5390)
    for i in range(400):
        s = r2.normal(0, SIGMA, 20).std(ddof=1)
        n = int(n_for(np.array([s]))[0])
        a = r2.normal(0, SIGMA, (500, n)); b = r2.normal(DELTA, SIGMA, (500, n))
        p = stats.ttest_ind(a, b, axis=1).pvalue
        chk.append(dict(n=n, power_calc=float(power(np.array([n]))[0]), power_sim=float((p < 0.05).mean())))
    ck = pd.DataFrame(chk); ck.to_csv(RES / "check_m20.csv", index=False, float_format="%.6f")
    json.dump({"n_true": n_true, "power_at_n_true": float(power(np.array([n_true]))[0]), "rows": sm.round(6).to_dict("records"),
               "check_m20": {"mean_calc": float(ck.power_calc.mean()), "mean_sim": float(ck.power_sim.mean()),
                             "max_abs_diff": float((ck.power_calc - ck.power_sim).abs().max())}},
              open(RES / "a539_main.json", "w"), ensure_ascii=False, indent=1)

    # 図1：検出力の分布（m=10・30・100、s をそのまま）
    fig, ax = plt.subplots(figsize=(8, 4))
    bins = np.linspace(0, 1, 41)
    for m, col in [(10, ORANGE), (30, BLUE), (100, INK)]:
        ax.hist(keep[(m, "plain")], bins=bins, histtype="step", lw=1.8, color=col, density=True, label=f"予備 {m}人")
    ax.axvline(0.8, color=GRAY, ls=":")
    ax.set_xlabel("本番の検出力"); ax.set_ylabel("密度")
    ax.legend(frameon=False, fontsize=9)
    ax.set_title("「80%のつもり」で決めた人数の、本番の検出力の分布")
    save(fig, "a539_power_dist.png", SRC + f"。本当の σ=1・差 0.4、σ を知っていれば各群 {n_true}人")

    # 図2：80%・70%を下回る割合
    fig, ax = plt.subplots(figsize=(7.5, 4))
    for rule, col, lab in [("plain", ORANGE, "s をそのまま"), ("ucl80", BLUE, "s の上側80%信頼限界")]:
        t = sm[sm.rule == rule]
        ax.plot(t.m, t.share_below80 * 100, "o-", color=col, label=lab + "：80%未満")
        ax.plot(t.m, t.share_below70 * 100, "s--", color=col, alpha=0.7, label=lab + "：70%未満")
        for x, v in zip(t.m, t.share_below70 * 100):
            ax.text(x, v + 2, f"{v:.0f}%", ha="center", fontsize=8, color=col)
    ax.set_xscale("log"); ax.set_xticks(MS); ax.set_xticklabels(MS)
    ax.set_xlabel("予備の調査の人数"); ax.set_ylabel("本番の検出力が下回る割合（%）")
    ax.set_ylim(0, 70); ax.legend(frameon=False, fontsize=8)
    ax.set_title("80%を下回るのはいつも半分強。大きく下回るのは予備が小さいとき")
    save(fig, "a539_share_below80.png", SRC + "。数字は70%未満の割合")

    # 図3：人数の代わり（平均の人数と検出力の10%点）
    fig, axs = plt.subplots(1, 2, figsize=(9, 3.8))
    for rule, col, lab in [("plain", ORANGE, "そのまま"), ("ucl80", BLUE, "上側80%")]:
        t = sm[sm.rule == rule]
        axs[0].plot(t.m, t.n_mean, "o-", color=col, label=lab)
        axs[1].plot(t.m, t.power_p10 * 100, "o-", color=col, label=lab)
    axs[0].axhline(n_true, color=GRAY, ls=":"); axs[0].set_ylabel("各群の人数（平均）")
    axs[1].axhline(80, color=GRAY, ls=":"); axs[1].set_ylabel("検出力の下位10%点（%）")
    for ax in axs:
        ax.set_xscale("log"); ax.set_xticks(MS); ax.set_xticklabels(MS); ax.set_xlabel("予備の調査の人数")
    axs[0].legend(frameon=False, fontsize=9)
    fig.suptitle("上側の限界で決めると、人数は増えるが下振れは小さくなる", y=1.02)
    save(fig, "a539_n_and_p10.png", SRC + f"。点線は σ を知っている場合（{n_true}人・80%）")
    print(sm.round(4).to_string()); print(ck.mean())


if __name__ == "__main__":
    main()

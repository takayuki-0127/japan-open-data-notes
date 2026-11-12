"""A347 災害の多い年と少ない年があるとき、件数をポアソンで見ると備えはどれだけ足りなくなるか（架空、seed 347）"""
import json
import numpy as np, pandas as pd
from scipy import stats, optimize, special
import matplotlib.pyplot as plt
from common import *

SEED = 347
LAM = 10.0                     # 年の災害件数の平均
KS = [np.inf, 20, 10, 5, 2, 1]  # 年による当たり外れの強さ（小さいほど強い）。分散＝平均×(1＋平均/k)
REPS = 2000
SEV_SIG = 1.2                  # 1件の損害額：対数正規（平均1）

def true_q(k, p):
    if np.isinf(k): return stats.poisson.ppf(p, LAM)
    return stats.nbinom.ppf(p, k, k / (k + LAM))

def draw_counts(rng, k, size):
    if np.isinf(k): return rng.poisson(LAM, size)
    g = rng.gamma(k, 1 / k, size)          # 年ごとの当たり外れ（平均1）
    return rng.poisson(LAM * g)

def fit_nb(x):
    """負の二項分布の最尤推定。分散が平均以下ならポアソンに戻す（k=inf）"""
    m, v = x.mean(), x.var(ddof=1)
    if v <= m * 1.0001: return m, np.inf
    def nll(logk):
        k = np.exp(logk)
        return -np.sum(special.gammaln(x + k) - special.gammaln(k) - special.gammaln(x + 1)
                       + k * np.log(k / (k + m)) + x * np.log(m / (k + m)))
    r = optimize.minimize_scalar(nll, bounds=(np.log(0.05), np.log(1e4)), method="bounded")
    k = float(np.exp(r.x))
    return m, (np.inf if k > 5e3 else k)

def q_from(m, k, p):
    if np.isinf(k): return stats.poisson.ppf(p, m)
    return stats.nbinom.ppf(p, k, k / (k + m))

def agg_q(rng, k, p, n=400000):
    """1年の損害額の合計の p 点（シミュレーション）"""
    c = draw_counts(rng, k, n)
    mu = -SEV_SIG ** 2 / 2
    x = rng.lognormal(mu, SEV_SIG, int(c.sum()))
    tot = np.bincount(np.repeat(np.arange(n), c), weights=x, minlength=n)
    return float(np.quantile(tot, p)), tot

def main():
    rng = np.random.default_rng(SEED)
    # 1) 本当の分布が分かっているとき：ポアソンで置いた99%点は、どれだけ小さいか
    A = []
    qp99 = stats.poisson.ppf(0.99, LAM); qp995 = stats.poisson.ppf(0.995, LAM)
    aggP, _ = agg_q(rng, np.inf, 0.99)
    for k in KS:
        qt = true_q(k, 0.99)
        exceed = float(stats.poisson.sf(qp99, LAM)) if np.isinf(k) else float(stats.nbinom.sf(qp99, k, k / (k + LAM)))
        aggT, tot = agg_q(rng, k, 0.99)
        exceed_agg = float((tot > aggP).mean())
        A.append(dict(k=("inf" if np.isinf(k) else k), var_over_mean=(1.0 if np.isinf(k) else 1 + LAM / k),
                      q99_true=float(qt), q99_poisson=float(qp99), short_pct=float((qp99 / qt - 1) * 100),
                      exceed_prob=exceed, once_in_years=float(1 / exceed),
                      agg99_true=aggT, agg99_poisson=aggP, agg_short_pct=float((aggP / aggT - 1) * 100),
                      agg_exceed_prob=exceed_agg, mean_agg=float(tot.mean())))
    dA = pd.DataFrame(A); dA.to_csv(RES / "true_vs_poisson.csv", index=False)

    # 2) 過去 T 年の件数から見積もるとき
    B = []
    for k in [np.inf, 5, 2]:
        qt = true_q(k, 0.99)
        for T in [10, 20, 50, 100]:
            x = draw_counts(rng, k, (REPS, T))
            qP = np.empty(REPS); qN = np.empty(REPS); isP = np.zeros(REPS, bool); disp = np.empty(REPS)
            for i in range(REPS):
                m, kh = fit_nb(x[i])
                qP[i] = stats.poisson.ppf(0.99, m); qN[i] = q_from(m, kh, 0.99); isP[i] = np.isinf(kh)
                disp[i] = x[i].var(ddof=1) / m
            # 分散÷平均の検定（ポアソンなら (T-1)×分散/平均 がカイ二乗に従う）で、当たり外れに気づけた割合
            pval = stats.chi2.sf((T - 1) * disp, T - 1)
            B.append(dict(k=("inf" if np.isinf(k) else k), T=T, q99_true=float(qt),
                          poisson_med=float(np.median(qP)), poisson_short_pct=float((np.median(qP) / qt - 1) * 100),
                          nb_p10=float(np.quantile(qN, 0.1)), nb_med=float(np.median(qN)), nb_p90=float(np.quantile(qN, 0.9)),
                          nb_below_true=float((qN < qt).mean()), poisson_below_true=float((qP < qt).mean()),
                          nb_collapsed=float(isP.mean()), detect_5pct=float((pval < 0.05).mean()),
                          nb_rmse_pct=float(np.sqrt(np.mean((qN / qt - 1) ** 2)) * 100),
                          poisson_rmse_pct=float(np.sqrt(np.mean((qP / qt - 1) ** 2)) * 100)))
    dB = pd.DataFrame(B); dB.to_csv(RES / "estimated_from_history.csv", index=False)

    # 例のデータ：50年分の件数（当たり外れなし／あり k=2）
    r2 = np.random.default_rng(SEED + 1)
    ex = pd.DataFrame({"year": np.arange(1, 51), "当たり外れなし": draw_counts(r2, np.inf, 50), "当たり外れあり": draw_counts(r2, 2, 50)})
    ex.to_csv(DATA / "example_counts_50y.csv", index=False)
    json.dump(dict(seed=SEED, lam=LAM, reps=REPS, sev_sigma=SEV_SIG, true_vs_poisson=dA.to_dict("records"),
                   estimated=dB.to_dict("records")), open(RES / "main.json", "w"), ensure_ascii=False, indent=1)

    src = "架空のデータ（作成者が乱数で作成、seed 347）。年の災害件数の平均は10件"
    # 図1：件数の分布（ポアソンと、当たり外れのある分布）
    fig, ax = plt.subplots(figsize=(8, 4.4))
    xs = np.arange(0, 46)
    ax.bar(xs - 0.2, stats.poisson.pmf(xs, LAM) * 100, width=0.4, color=LIGHT, label="当たり外れなし（ポアソン）")
    ax.bar(xs + 0.2, stats.nbinom.pmf(xs, 2, 2 / (2 + LAM)) * 100, width=0.4, color=ORANGE, label="当たり外れあり（分散が平均の6倍）")
    for q, c, t in [(qp99, BLUE, f"ポアソンの99%点：{qp99:.0f}件"), (true_q(2, 0.99), ORANGE, f"本当の99%点：{true_q(2,0.99):.0f}件")]:
        ax.axvline(q + 0.5, color=c, lw=1.2, ls="--"); ax.text(q + 1, 10.5 if c == BLUE else 8.5, t, color=c, fontsize=9.5)
    ax.set_xlabel("1年の災害の件数"); ax.set_ylabel("その件数になる年の割合（%）"); ax.legend(fontsize=9, frameon=False, loc="upper right", bbox_to_anchor=(1.0, 0.72))
    ax.set_title("平均は同じ10件でも、多い年の出方がまったく違う")
    save(fig, "a347_count_distributions.png", src)

    # 図2：当たり外れの強さと、ポアソンの99%点の不足
    fig, ax = plt.subplots(figsize=(8, 4.4))
    lab = ["なし\n(1倍)"] + [f"{1+LAM/k:.1f}倍" for k in KS[1:]]
    x = np.arange(len(KS)); w = 0.38
    b1 = ax.bar(x - w / 2, -dA.short_pct, w, color=BLUE, label="件数の99%点の不足")
    b2 = ax.bar(x + w / 2, -dA.agg_short_pct, w, color=ORANGE, label="損害額の合計の99%点の不足")
    for r_, v in zip(list(b1) + list(b2), list(-dA.short_pct) + list(-dA.agg_short_pct)):
        ax.text(r_.get_x() + r_.get_width() / 2, v + 0.8, f"{abs(v):.0f}%", ha="center", fontsize=9)
    for xi, e in zip(x, dA.once_in_years): ax.text(xi, -7.5, f"実際は\n{e:.0f}年に1度", ha="center", fontsize=8.5, color=GRAY)
    ax.set_xticks(x); ax.set_xticklabels(lab); ax.set_ylim(-11, 75)
    ax.set_xlabel("年による当たり外れの強さ（件数の分散÷平均）"); ax.set_ylabel("ポアソンで置いた「100年に1度」が\n本当の値より小さい幅（%）")
    ax.legend(fontsize=9, frameon=False, loc="upper left"); ax.axhline(0, color=INK, lw=0.6)
    ax.set_title("当たり外れが強いほど、ポアソンの「100年に1度」は足りなくなる")
    save(fig, "a347_shortfall_by_dispersion.png", src, y=-0.08)

    # 図3：過去 T 年から見積もった99%点（k=2）
    fig, ax = plt.subplots(figsize=(8, 4.4))
    d = dB[dB.k == 2]; x = np.arange(len(d)); qt = d.q99_true.iloc[0]
    ax.axhline(qt, color=INK, lw=1); ax.text(3.45, qt + 0.8, f"本当の99%点 {qt:.0f}件", ha="right", fontsize=9)
    ax.errorbar(x + 0.12, d.nb_med, yerr=[d.nb_med - d.nb_p10, d.nb_p90 - d.nb_med], fmt="o", color=ORANGE, capsize=4, lw=2, label="負の二項分布を当てはめ（線は10〜90%の範囲）")
    ax.plot(x - 0.12, d.poisson_med, "s", color=BLUE, label="ポアソンで置く（中央値）")
    for xi, (a, b, c, col) in zip(x, zip(d.nb_p10, d.nb_p90, d.nb_collapsed, d.detect_5pct)):
        ax.text(xi + 0.22, b + 0.3, f"{a:.0f}〜{b:.0f}件", fontsize=9, color=ORANGE)
    ax.set_xticks(x); ax.set_xticklabels([f"過去{t}年" for t in d["T"]]); ax.set_ylabel("見積もった「100年に1度」の件数"); ax.set_ylim(10, 62)
    ax.legend(fontsize=9, frameon=False, loc="upper right"); ax.set_title("負の二項分布なら近づくが、20年分では幅が広い（分散が平均の6倍の場合）")
    save(fig, "a347_estimated_from_history.png", src)
    print(dA.round(3).to_string()); print(dB.round(3).to_string())

if __name__ == "__main__":
    main()

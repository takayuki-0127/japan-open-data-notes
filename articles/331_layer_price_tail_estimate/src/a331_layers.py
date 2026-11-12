"""331 大きな損害だけを受け持つ「層」の期待損害は、裾の見積もりにどれだけ左右されるか（架空のデータ、seed 331）"""
import json
import numpy as np, pandas as pd
from scipy import stats, optimize
from common import *

SEED, REPS = 331, 1000
NS = [50, 200, 1000]
LAYERS = [(0, 10), (10, 20), (20, 50), (50, 100), (100, 200)]          # 百万円。[下端, 上端)
LAB = ["0〜10", "10〜20", "20〜50", "50〜100", "100〜200"]
XI, SIG = 0.4, 3.0                                                     # 本当の分布A：GPD（平均 5 百万円）
LN_S = 1.34; LN_M = np.log(5.0) - LN_S ** 2 / 2                        # 本当の分布B：対数正規（平均 5、変動係数は A とほぼ同じ）


def gpd_layer(xi, sig, a, b):
    """GPD（位置0）の1事故あたりの層 [a,b) の期待損害＝∫_a^b S(x)dx"""
    xi = np.asarray(xi, float); sig = np.asarray(sig, float)
    def G(x):                                                          # ∫_0^x S(t)dt
        with np.errstate(all="ignore"):
            if_exp = sig * (1 - np.exp(-x / sig))
            base = np.clip(1 + xi * x / sig, 0, None)                  # ξ<0 は上限 −σ/ξ で打ち止め
            gen = sig / (1 - xi) * (1 - base ** (1 - 1 / xi))
            near1 = sig * np.log1p(x / sig)                            # ξ=1
        return np.where(np.abs(xi) < 1e-6, if_exp, np.where(np.abs(xi - 1) < 1e-6, near1, gen))
    return G(b) - G(a)


def ln_lev(mu, s, d):
    """対数正規の E[min(X,d)]"""
    return np.exp(mu + s ** 2 / 2) * stats.norm.cdf((np.log(d) - mu - s ** 2) / s) + d * stats.norm.sf((np.log(d) - mu) / s)


def ln_layer(mu, s, a, b):
    return ln_lev(mu, s, b) - (ln_lev(mu, s, a) if a > 0 else 0.0)


def fit_gpd(x):
    """GPD（位置0）の最尤法。(ξ, σ)"""
    def nll(p):
        xi, ls = p; sig = np.exp(ls)
        if abs(xi) < 1e-8: return len(x) * ls + x.sum() / sig
        z = 1 + xi * x / sig
        if (z <= 0).any(): return 1e12
        return len(x) * ls + (1 + 1 / xi) * np.log(z).sum()
    best = None
    for x0 in ([0.2, np.log(x.mean() * 0.8)], [0.6, np.log(np.median(x))]):
        r = optimize.minimize(nll, x0, method="Nelder-Mead", options={"xatol": 1e-5, "fatol": 1e-7, "maxiter": 600})
        if best is None or r.fun < best.fun: best = r
    return best.x[0], np.exp(best.x[1])


def run(truth):
    rng = np.random.default_rng(SEED + (0 if truth == "GPD" else 1))
    if truth == "GPD":
        draw = lambda n: stats.genpareto.rvs(XI, scale=SIG, size=n, random_state=rng)
        true = np.array([gpd_layer(XI, SIG, a, b) for a, b in LAYERS])
    else:
        draw = lambda n: rng.lognormal(LN_M, LN_S, n)
        true = np.array([ln_layer(LN_M, LN_S, a, b) for a, b in LAYERS])
    out = {}
    for n in NS:
        est = {k: np.empty((REPS, len(LAYERS))) for k in ("gpd", "lognormal", "empirical")}
        xis = np.empty(REPS)
        for r in range(REPS):
            x = draw(n)
            xi, sig = fit_gpd(x); xis[r] = xi
            lx = np.log(x); mu, s = lx.mean(), lx.std()
            for j, (a, b) in enumerate(LAYERS):
                est["gpd"][r, j] = gpd_layer(xi, sig, a, b)
                est["lognormal"][r, j] = ln_layer(mu, s, a, b)
                est["empirical"][r, j] = np.clip(x - a, 0, b - a).mean()   # 実績そのまま
        out[n] = (est, xis)
    return true, out


def summarize(true, out):
    rows = []
    for n, (est, xis) in out.items():
        for m, e in est.items():
            ratio = e / true
            for j, lab in enumerate(LAB):
                r = ratio[:, j]
                rows.append(dict(n=n, method=m, layer=lab, true=true[j], median_ratio=np.median(r), mean_ratio=r.mean(),
                                 p10=np.quantile(r, .1), p90=np.quantile(r, .9), spread=np.quantile(r, .9) / max(np.quantile(r, .1), 1e-12),
                                 rmse_pct=100 * np.sqrt(((r - 1) ** 2).mean()), zero_share=float((e[:, j] == 0).mean()),
                                 within_25pct=float((np.abs(r - 1) <= .25).mean())))
    return pd.DataFrame(rows)


def main():
    res = {}; tabs = {}
    for truth in ("GPD", "lognormal"):
        true, out = run(truth)
        df = summarize(true, out); df.insert(0, "truth", truth); tabs[truth] = df
        res[truth] = dict(true_layer_loss=dict(zip(LAB, true.round(5).tolist())),
                          xi_hat={str(n): dict(median=float(np.median(x)), p10=float(np.quantile(x, .1)), p90=float(np.quantile(x, .9)),
                                               share_ge_1=float((x >= 1).mean())) for n, (_, x) in out.items()})
        if truth == "GPD":                                             # 例のデータ1組（200件）
            x = stats.genpareto.rvs(XI, scale=SIG, size=200, random_state=np.random.default_rng(SEED))
            pd.DataFrame({"loss_mil_yen": np.sort(x).round(4)}).to_csv(DATA / "example_losses_200.csv", index=False)
    allt = pd.concat(tabs.values()); allt.round(5).to_csv(RES / "layer_errors.csv", index=False)
    g = tabs["GPD"]; q = lambda n, m, lab, c: float(g[(g.n == n) & (g.method == m) & (g.layer == lab)][c].iloc[0])
    res["headline"] = {f"n{n}": {lab: dict(p10=q(n, "gpd", lab, "p10"), p90=q(n, "gpd", lab, "p90"), rmse_pct=q(n, "gpd", lab, "rmse_pct"),
                                          within_25pct=q(n, "gpd", lab, "within_25pct")) for lab in LAB} for n in NS}
    res["rmse_top_over_bottom"] = {str(n): q(n, "gpd", LAB[-1], "rmse_pct") / q(n, "gpd", LAB[0], "rmse_pct") for n in NS}
    res["settings"] = dict(seed=SEED, reps=REPS, ns=NS, layers=LAYERS, gpd=dict(xi=XI, sigma=SIG), lognormal=dict(mu=LN_M, sigma=LN_S))
    json.dump(res, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)

    # 図1：GPD を当てはめたときの 見積もり÷正解（10〜90%の範囲）
    fig, ax = plt.subplots(figsize=(8.2, 4.6)); col = {50: ORANGE, 200: BLUE, 1000: GREEN}
    for k, n in enumerate(NS):
        d = g[(g.n == n) & (g.method == "gpd")]
        y = np.arange(len(LAB)) + (k - 1) * 0.24
        ax.hlines(y, np.maximum(d.p10, 0.03), d.p90, color=col[n], lw=5, alpha=.85, label=f"{n:,}件")
        ax.plot(d.median_ratio, y, "o", color=INK, ms=4)
    ax.axvline(1, color=GRAY, lw=1); ax.set_xscale("log"); ax.set_yticks(range(len(LAB))); ax.set_yticklabels([l + "百万円" for l in LAB])
    ax.set_xlim(0.03, 12); ax.set_xticks([0.1, 0.3, 1, 3, 10]); ax.set_xticklabels(["0.1倍", "0.3倍", "正解", "3倍", "10倍"]); ax.minorticks_off()
    ax.set_xlabel("層の期待損害の見積もり ÷ 正解（帯は1,000回の10〜90%、点は中央値）"); ax.legend(title="損害データの件数", frameon=False, loc="lower left", fontsize=9)
    ax.set_title("上の層ほど、見積もりの幅が広がる（本当の分布と同じ形を当てはめた場合）")
    save(fig, "a331_layer_spread.png", "架空のデータ（本当の分布は GPD ξ=0.4、seed 331）。50件の上2つの層は、帯の左端が図の外（0.03倍より下）にある")

    # 図2：方法ごとの誤差の大きさ（RMSE）
    fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.9), sharey=True)
    name = {"gpd": "GPD を当てはめ", "lognormal": "対数正規を当てはめ", "empirical": "実績そのまま"}; mc = {"gpd": BLUE, "lognormal": ORANGE, "empirical": GRAY}
    for ax, n in zip(axes, NS):
        for m in name:
            d = g[(g.n == n) & (g.method == m)]
            ax.plot(range(len(LAB)), d.rmse_pct, "o-", color=mc[m], label=name[m])
        ax.set_yscale("log"); ax.set_title(f"{n:,}件"); ax.set_xticks(range(len(LAB))); ax.set_xticklabels(LAB, fontsize=8)
        ax.set_yticks([5, 10, 20, 50, 100, 200, 500]); ax.set_yticklabels(["5%", "10%", "20%", "50%", "100%", "200%", "500%"])
    axes[0].set_ylabel("誤差の大きさ（RMSE）"); axes[0].legend(frameon=False, fontsize=8.5); axes[1].set_xlabel("層（百万円）")
    fig.suptitle("データが増えると誤差は縮むが、上の層ほど大きいのは変わらない", y=1.02)
    save(fig, "a331_rmse_by_method.png", "架空のデータ（本当の分布は GPD ξ=0.4）。RMSE は、見積もり÷正解−1 を二乗して平均し平方根をとったもの", y=-0.06)

    # 図3：分布の形を取り違えたとき（1,000件、中央値）
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.9), sharey=True)
    for ax, truth, ttl in zip(axes, ("GPD", "lognormal"), ("本当は GPD（裾がべき乗で落ちる）", "本当は対数正規")):
        t = tabs[truth]
        for m in ("gpd", "lognormal"):
            d = t[(t.n == 1000) & (t.method == m)]
            ax.plot(range(len(LAB)), d.median_ratio, "o-", color=mc[m], label=name[m])
        ax.axhline(1, color=GRAY, lw=1); ax.set_title(ttl, fontsize=11); ax.set_xticks(range(len(LAB))); ax.set_xticklabels(LAB, fontsize=8)
        ax.set_xlabel("層（百万円）")
    axes[0].set_ylabel("見積もり ÷ 正解（中央値）"); axes[0].legend(frameon=False, fontsize=9)
    fig.suptitle("1,000件あっても、分布の形を取り違えると上の層でずれる", y=1.02)
    save(fig, "a331_wrong_family.png", "架空のデータ。2つの本当の分布は、平均（5百万円）と変動係数がほぼ同じ", y=-0.06)
    print(json.dumps(res["rmse_top_over_bottom"]), res["GPD"]["xi_hat"])
    print(g[(g.method == "gpd")][["n", "layer", "true", "median_ratio", "p10", "p90", "rmse_pct", "within_25pct"]].round(3).to_string())
    print(allt[(allt.n == 1000) & (allt.method != "empirical")][["truth", "method", "layer", "median_ratio", "rmse_pct"]].round(3).to_string())
    print(g[(g.method != "gpd")][["n", "method", "layer", "median_ratio", "rmse_pct", "zero_share"]].round(3).to_string())


if __name__ == "__main__":
    main()

"""466 「200年に1度の値」（99.5%点）と「それを超えたときの平均」の見積もりの振れを比べる（架空の年間損害、seed 466）"""
import json
import numpy as np, pandas as pd
from scipy import stats
from common import *

SEED = 466
P = 0.995
MEAN = 100.0   # 年間損害の平均を100にそろえる
SRC = "架空の年間損害（作成者が乱数で作成、seed 466）"


def lognormal(sigma):
    mu = np.log(MEAN) - sigma ** 2 / 2
    def draw(rng, size): return rng.lognormal(mu, sigma, size)
    def var(p): return float(np.exp(mu + sigma * stats.norm.ppf(p)))
    def es(p): return float(MEAN * stats.norm.cdf(sigma - stats.norm.ppf(p)) / (1 - p))
    return draw, var, es


def pareto(alpha):
    xm = MEAN * (alpha - 1) / alpha
    def draw(rng, size): return xm * (1 - rng.random(size)) ** (-1 / alpha)
    def var(p): return float(xm * (1 - p) ** (-1 / alpha))
    def es(p): return float(alpha / (alpha - 1) * var(p))
    return draw, var, es


DISTS = {"対数正規 σ=0.5": lognormal(0.5), "対数正規 σ=1.0": lognormal(1.0), "対数正規 σ=1.5": lognormal(1.5),
         "パレート α=3.0": pareto(3.0), "パレート α=2.2": pareto(2.2)}
NS = [1000, 2000, 5000, 10000, 20000, 50000, 100000]
REPS = {1000: 4000, 2000: 4000, 5000: 3000, 10000: 2000, 20000: 1000, 50000: 600, 100000: 400}


def estimate(x, p):
    """x は（回数, 年数）。経験的な p 点と、それを超えた分の平均"""
    n = x.shape[1]
    k = int(np.ceil(n * p))                    # 小さいほうから k 番目が p 点
    part = np.partition(x, k - 1, axis=1)
    v = part[:, k - 1]
    tail = part[:, k:]                         # p 点より上の n-k 個
    return v, tail.mean(axis=1), n - k


def run():
    rng = np.random.default_rng(SEED)
    rows, keep = [], {}
    for name, (draw, var, es) in DISTS.items():
        tv, te, te99 = var(P), es(P), es(0.99)
        for n in NS:
            R = REPS[n]; vs, es_, e99 = [], [], []
            for start in range(0, R, 200):
                x = draw(rng, (min(200, R - start), n))
                v, e, m = estimate(x, P); _, e2, _ = estimate(x, 0.99)
                vs.append(v); es_.append(e); e99.append(e2)
            v, e, e2 = np.concatenate(vs), np.concatenate(es_), np.concatenate(e99)
            if n in (1000, 10000): keep[(name, n)] = (v / tv - 1, e / te - 1)
            f = lambda est, t: (np.sqrt(np.mean((est / t - 1) ** 2)) * 100, (est.mean() / t - 1) * 100,
                                (np.median(est) / t - 1) * 100, np.mean(est < t) * 100)
            rv, re_, r99 = f(v, tv), f(e, te), f(e2, te99)
            rows.append(dict(分布=name, 年数=n, 回数=R, 超えた年の数=m, 正解_99_5点=round(tv, 1), 正解_超過平均=round(te, 1),
                             正解_99超過平均=round(te99, 1),
                             RMSE_99_5点=round(rv[0], 2), RMSE_超過平均=round(re_[0], 2), RMSE_99超過平均=round(r99[0], 2),
                             偏り_99_5点=round(rv[1], 2), 偏り_超過平均=round(re_[1], 2), 偏り_99超過平均=round(r99[1], 2),
                             中央値のずれ_99_5点=round(rv[2], 2), 中央値のずれ_超過平均=round(re_[2], 2),
                             小さく出た割合_99_5点=round(rv[3], 1), 小さく出た割合_超過平均=round(re_[3], 1),
                             RMSEの比=round(re_[0] / rv[0], 2), 同じ振れに要る年数の比=round((re_[0] / rv[0]) ** 2, 2)))
    df = pd.DataFrame(rows); df.to_csv(RES / "var_es_rmse.csv", index=False)
    return df, keep


def example(rng):
    """例：対数正規 σ=1.0 の1,000年分を1つ"""
    draw, var, es = DISTS["対数正規 σ=1.0"]
    x = np.sort(draw(rng, 1000))[::-1][:20]
    pd.DataFrame({"大きい順": np.arange(1, 21), "年間損害": np.round(x, 1)}).to_csv(DATA / "example_top20_of_1000_years.csv", index=False)


def figs(df, keep):
    names = list(DISTS)
    # 図1：1万年分の RMSE
    d = df[df.年数 == 10000].set_index("分布").loc[names]
    fig, ax = plt.subplots(figsize=(8.6, 4.2)); x = np.arange(len(names)); w = 0.27
    for i, (c, lab, col) in enumerate([("RMSE_99_5点", "99.5%点（200年に1度の値）", BLUE), ("RMSE_超過平均", "99.5%点を超えた年の平均", ORANGE),
                                       ("RMSE_99超過平均", "99%点を超えた年の平均", GRAY)]):
        b = ax.bar(x + (i - 1) * w, d[c], w, color=col, label=lab)
        for r in b: ax.text(r.get_x() + r.get_width() / 2, r.get_height() + 0.3, f"{r.get_height():.1f}", ha="center", fontsize=8)
    ax.set_xticks(x); ax.set_xticklabels([n.replace(" ", "\n") for n in names]); ax.set_ylabel("正解からのずれ（RMSE、%）")
    ax.set_title("1万年分のシミュレーションから出した見積もりの振れ"); ax.legend(frameon=False, fontsize=9)
    save(fig, "a466_rmse_10000.png", SRC + "。正解は式の値。各2,000回")
    # 図2：年数と RMSE
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
    for ax, name in zip(axes, ["対数正規 σ=1.0", "パレート α=2.2"]):
        d = df[df.分布 == name]
        ax.plot(d.年数, d.RMSE_99_5点, "o-", color=BLUE, label="99.5%点")
        ax.plot(d.年数, d.RMSE_超過平均, "s-", color=ORANGE, label="99.5%点を超えた年の平均")
        ax.plot(d.年数, d.RMSE_99超過平均, "^--", color=GRAY, label="99%点を超えた年の平均")
        ax.set_xscale("log"); ax.set_yscale("log"); ax.set_title(name); ax.set_xlabel("シミュレーションの年数（対数の目盛り）")
        ax.set_yticks([1, 2, 5, 10, 20, 50]); ax.set_yticklabels(["1", "2", "5", "10", "20", "50"])
    axes[0].set_ylabel("正解からのずれ（RMSE、%、対数の目盛り）"); axes[0].legend(frameon=False, fontsize=9)
    fig.suptitle("年数を増やしたときの振れ", y=1.02)
    save(fig, "a466_rmse_by_years.png", SRC)
    # 図3：1,000年分の見積もりの散らばり
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
    for ax, name in zip(axes, ["対数正規 σ=1.0", "パレート α=2.2"]):
        v, e = keep[(name, 1000)]
        bins = np.linspace(-80, 200, 57)
        ax.hist(np.clip(v * 100, -80, 200), bins=bins, color=BLUE, alpha=0.6, label="99.5%点")
        ax.hist(np.clip(e * 100, -80, 200), bins=bins, color=ORANGE, alpha=0.6, label="99.5%点を超えた年の平均（5年分の平均）")
        ax.axvline(0, color=INK, lw=1); ax.set_title(name + "、1,000年分"); ax.set_xlabel("正解からのずれ（%）。200%以上は右端にまとめた")
    axes[0].set_ylabel("回数（4,000回のうち）"); axes[0].legend(frameon=False, fontsize=8.5)
    fig.suptitle("1,000年分から出した見積もりの散らばり", y=1.02)
    save(fig, "a466_spread_1000.png", SRC)


if __name__ == "__main__":
    df, keep = run()
    example(np.random.default_rng(SEED + 1))
    g = lambda name, n, c: float(df[(df.分布 == name) & (df.年数 == n)][c].iloc[0])
    main = {"p": P, "truth": {k: {"var995": round(v[1](P), 1), "es995": round(v[2](P), 1), "es99": round(v[2](0.99), 1)} for k, v in DISTS.items()},
            "rmse_10000": {k: {"var": g(k, 10000, "RMSE_99_5点"), "es": g(k, 10000, "RMSE_超過平均"), "es99": g(k, 10000, "RMSE_99超過平均"),
                               "years_ratio": g(k, 10000, "同じ振れに要る年数の比")} for k in DISTS},
            "rmse_1000": {k: {"var": g(k, 1000, "RMSE_99_5点"), "es": g(k, 1000, "RMSE_超過平均"), "bias_es": g(k, 1000, "偏り_超過平均"),
                              "median_es": g(k, 1000, "中央値のずれ_超過平均"), "low_es": g(k, 1000, "小さく出た割合_超過平均"),
                              "bias_var": g(k, 1000, "偏り_99_5点")} for k in DISTS},
            "rmse_100000": {k: {"var": g(k, 100000, "RMSE_99_5点"), "es": g(k, 100000, "RMSE_超過平均")} for k in DISTS}}
    json.dump(main, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)
    figs(df, keep)
    print(json.dumps(main, ensure_ascii=False, indent=1))
    print(df[["分布", "年数", "RMSE_99_5点", "RMSE_超過平均", "RMSE_99超過平均", "偏り_超過平均", "中央値のずれ_超過平均", "小さく出た割合_超過平均", "同じ振れに要る年数の比"]].to_string())

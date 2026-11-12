"""A380 ブートストラップの区間は、件数が少ない・裾が重いデータで何%当たるのか
真の平均・中央値が分かっている架空のデータ（正規・対数正規・パレート）で、95%区間が真の値を含む割合を数える。
比べる区間：パーセンタイル法、基本法、BCa 法、t 分布の区間（平均）、順位にもとづく区間（中央値）。乱数の種は380。
"""
import json, sys, time
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
from common import DATA, FIG, RES, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, save

SEED, B = 380, 999
SRC = "架空のデータ（作成者が乱数で作成、seed 380）"
NS = [10, 20, 50, 100, 300, 1000]
REPS = {10: 2000, 20: 2000, 50: 2000, 100: 2000, 300: 2000, 1000: 2000}
DISTS = {
    "正規": dict(draw=lambda rng, size: rng.normal(0, 1, size), mean=0.0, median=0.0),
    "対数正規（σ=1）": dict(draw=lambda rng, size: rng.lognormal(0, 1, size), mean=float(np.exp(0.5)), median=1.0),
    "パレート（α=2.5）": dict(draw=lambda rng, size: 1 + rng.pareto(2.5, size), mean=2.5 / 1.5, median=2 ** (1 / 2.5)),
    "パレート（α=1.5）": dict(draw=lambda rng, size: 1 + rng.pareto(1.5, size), mean=3.0, median=2 ** (1 / 1.5)),
}
ZA = stats.norm.ppf(0.975)


def loo_median(s):
    """s：行ごとに並べ替え済み（R, n）。1つ抜いたときの中央値（R, n）"""
    R, n = s.shape; out = np.empty((R, n))
    if n % 2 == 0:
        h = n // 2
        out[:, :h] = s[:, [h]]; out[:, h:] = s[:, [h - 1]]
    else:
        m = (n - 1) // 2
        out[:, :m] = (s[:, [m]] + s[:, [m + 1]]) / 2; out[:, m] = (s[:, m - 1] + s[:, m + 1]) / 2; out[:, m + 1:] = (s[:, [m - 1]] + s[:, [m]]) / 2
    return out


def kth(sorted_boot, alpha):
    """並べ替えた再標本の統計量（R, B）から、行ごとに alpha 点（R,）を取る。B=999 なので k=alpha×1000 番目"""
    k = np.clip(np.round(alpha * (B + 1)).astype(int), 1, B) - 1
    return sorted_boot[np.arange(len(k)), k]


def intervals(theta, boot, jack):
    """theta：元の標本の統計量（R,）、boot：再標本の統計量（R, B）、jack：1つ抜きの統計量（R, n）"""
    sb = np.sort(boot, axis=1); R = len(theta)
    lo_p = kth(sb, np.full(R, 0.025)); hi_p = kth(sb, np.full(R, 0.975))
    out = {"パーセンタイル法": (lo_p, hi_p), "基本法": (2 * theta - hi_p, 2 * theta - lo_p)}
    prop = ((boot < theta[:, None]).sum(1) + 0.5 * (boot == theta[:, None]).sum(1)) / B
    z0 = stats.norm.ppf(np.clip(prop, 1 / (2 * B), 1 - 1 / (2 * B)))
    d = jack.mean(1, keepdims=True) - jack
    den = 6 * (d ** 2).sum(1) ** 1.5
    a = np.where(den > 0, (d ** 3).sum(1) / np.where(den > 0, den, 1), 0.0)
    def adj(z):
        return stats.norm.cdf(z0 + (z0 + z) / (1 - a * (z0 + z)))
    out["BCa 法"] = (kth(sb, adj(-ZA)), kth(sb, adj(ZA)))
    return out


def run(dname, n, rng):
    spec = DISTS[dname]; reps = REPS[n]
    chunk = max(1, int(2e7 // (B * n)))
    acc = {}
    def add(stat, method, lo, hi, true):
        k = (stat, method); a = acc.setdefault(k, [0, 0, 0, 0.0, 0])
        a[0] += int(((lo <= true) & (true <= hi)).sum()); a[1] += int((true < lo).sum()); a[2] += int((true > hi).sum()); a[3] += float((hi - lo).sum()); a[4] += len(lo)
    done = 0
    while done < reps:
        R = min(chunk, reps - done); done += R
        x = spec["draw"](rng, (R, n)); s = np.sort(x, axis=1)
        idx = rng.integers(0, n, (R, B, n))
        xb = np.take_along_axis(x[:, None, :], idx, axis=2)
        # 平均
        th = x.mean(1); jack = (x.sum(1, keepdims=True) - x) / (n - 1)
        for m, (lo, hi) in intervals(th, xb.mean(2), jack).items(): add("平均", m, lo, hi, spec["mean"])
        sd = x.std(1, ddof=1); h = stats.t.ppf(0.975, n - 1) * sd / np.sqrt(n)
        add("平均", "t 分布の区間", th - h, th + h, spec["mean"])
        # 中央値
        th = np.median(x, axis=1)
        for m, (lo, hi) in intervals(th, np.median(xb, axis=2), loo_median(s)).items(): add("中央値", m, lo, hi, spec["median"])
        j = int(stats.binom.ppf(0.025, n, 0.5)); j = max(j, 1)            # 順位にもとづく区間（並べ替えた j 番目と n−j+1 番目）
        add("中央値", "順位にもとづく区間", s[:, j - 1], s[:, n - j], spec["median"])
    rows = []
    for (stat, m), (c, lo, hi, ln, tot) in acc.items():
        true = spec["mean"] if stat == "平均" else spec["median"]
        rows.append(dict(dist=dname, n=n, stat=stat, method=m, reps=tot, cover=c / tot * 100, true_below=lo / tot * 100, true_above=hi / tot * 100, mean_length=ln / tot))
    return rows


def main():
    if "--plot-only" in sys.argv:            # 計算済みの results/coverage.csv から、表と図だけ作り直す
        df = pd.read_csv(RES / "coverage.csv")
    else:
        rng = np.random.default_rng(SEED); rows = []; t0 = time.time()
        for dname in DISTS:
            for n in NS:
                rows += run(dname, n, rng); print(dname, n, round(time.time() - t0), flush=True)
        df = pd.DataFrame(rows); df.to_csv(RES / "coverage.csv", index=False)
        df = pd.read_csv(RES / "coverage.csv")   # 書き出した値と同じものを使う
    piv = df.pivot_table(index=["stat", "dist", "method"], columns="n", values="cover", sort=False).round(1)
    piv.to_csv(RES / "coverage_table.csv"); print(piv.to_string())
    above = df.pivot_table(index=["stat", "dist", "method"], columns="n", values="true_above", sort=False).round(1); above.to_csv(RES / "true_above_upper_bound.csv")
    # 例：対数正規・30件の1回分
    ex = np.random.default_rng(SEED + 1).lognormal(0, 1, 30); pd.DataFrame({"x": ex}).to_csv(DATA / "example_lognormal_30.csv", index=False)
    out = {"B": B, "reps": REPS, "true": {k: {"mean": v["mean"], "median": v["median"]} for k, v in DISTS.items()},
           "coverage": df.round(2).to_dict("records")}
    json.dump(out, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)

    cols = {"パーセンタイル法": BLUE, "基本法": GRAY, "BCa 法": ORANGE, "t 分布の区間": GREEN, "順位にもとづく区間": GREEN}
    for stat, fn, ttl in (("平均", "a380_coverage_mean.png", "平均の95%区間：裾が重いと、1,000件あっても95%に届かない"), ("中央値", "a380_coverage_median.png", "中央値の95%区間：裾が重くても変わらない。外れたのは基本法だけ")):
        fig, axes = plt.subplots(1, 4, figsize=(13, 3.9), sharey=True)
        for ax, dname in zip(axes, DISTS):
            g = df[(df.stat == stat) & (df.dist == dname)]
            for m in g.method.unique():
                h = g[g.method == m]; ax.plot(range(len(NS)), h.cover, color=cols[m], lw=2, marker="o", ms=4, label=m, ls="--" if m in ("t 分布の区間", "順位にもとづく区間") else "-")
            ax.axhline(95, color=INK, lw=0.8); ax.set_xticks(range(len(NS))); ax.set_xticklabels([f"{n:,}" for n in NS], fontsize=8); ax.set_title(dname, fontsize=10); ax.set_xlabel("件数")
        axes[0].set_ylabel("真の値を含んだ割合（%）"); axes[0].set_ylim(50 if stat == "平均" else 75, 100); axes[-1].legend(fontsize=8, frameon=False, loc="lower right")
        fig.suptitle(ttl, fontsize=12, y=1.02)
        save(fig, fn, SRC, y=-0.04)

    # 図3：外れ方の向き（対数正規・平均）
    g = df[(df.stat == "平均") & (df.dist == "対数正規（σ=1）")]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.0), sharey=True)
    for ax, col, ttl in zip(axes, ("true_above", "true_below"), ("真の平均が、区間の上の端より大きかった割合", "真の平均が、区間の下の端より小さかった割合")):
        for m in g.method.unique():
            h = g[g.method == m]; ax.plot(range(len(NS)), h[col], color=cols[m], lw=2, marker="o", ms=4, label=m, ls="--" if m == "t 分布の区間" else "-")
        ax.axhline(2.5, color=INK, lw=0.8); ax.set_xticks(range(len(NS))); ax.set_xticklabels([f"{n:,}" for n in NS]); ax.set_xlabel("件数"); ax.set_title(ttl, fontsize=10)
    axes[0].set_ylabel("割合（%。本来はどちらも2.5%）"); axes[1].legend(fontsize=8, frameon=False)
    fig.suptitle("外れるのは「上」ばかり：区間の上の端が低すぎる（対数正規の平均）", fontsize=12, y=1.02)
    save(fig, "a380_miss_direction.png", SRC, y=-0.04)


if __name__ == "__main__":
    main()

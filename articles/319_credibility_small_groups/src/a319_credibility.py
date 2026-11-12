"""319 小さな集団の事故率は、全体の平均にどれだけ寄せるのがよいか
架空の100集団（大きさがばらばら、本当の事故率が分かる）で、
「その集団の実績そのまま」「全体の平均」「信頼度の重みで混ぜる（ビュールマン・ストラウブ）」を比べる。"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import DATA, RES, BLUE, ORANGE, GRAY, GREEN, LIGHT, INK, save

SEED, NSIM, NG, MU = 319, 1000, 100, 0.05      # 100集団、全体の事故率は年5%
SOURCE = "架空のデータ（作成者が乱数で作成、seed 319）"
BINS = [(10, 50, "10〜49人"), (50, 200, "50〜199人"), (200, 1000, "200〜999人"), (1000, 20001, "1,000人以上")]


def make(rng, cv, nsim=NSIM, ng=NG):
    n = np.clip(np.round(rng.lognormal(np.log(200), 1.3, (nsim, ng))), 10, 20000)   # 集団の大きさ（人数）
    theta = rng.gamma(1 / cv ** 2, MU * cv ** 2, (nsim, ng))                        # 本当の事故率（集団ごとに違う）
    c1 = rng.poisson(n * theta); c2 = rng.poisson(n * theta)                        # 1年目・2年目の事故件数
    return n, theta, c1, c2


def credibility(n, c1):
    """ビュールマン・ストラウブの重み。件数はポアソンとみて、集団内のばらつき＝全体の事故率と置く"""
    m = c1.sum(1, keepdims=True) / n.sum(1, keepdims=True)                          # 全体の事故率
    x = c1 / n
    ntot = n.sum(1, keepdims=True); r = n.shape[1]
    vhm = ((n * (x - m) ** 2).sum(1, keepdims=True) - (r - 1) * m) / (ntot - (n ** 2).sum(1, keepdims=True) / ntot)
    vhm = np.maximum(vhm, 0)                                                        # 集団どうしの本当の差（負なら0）
    k = np.where(vhm > 0, m / np.where(vhm > 0, vhm, 1), np.inf)                    # 重みが0.5になる人数
    z = n / (n + k)
    return z * x + (1 - z) * m, k[:, 0], m, x


def wrmse(pred, target, n):
    return float(np.sqrt((n * (pred - target) ** 2).sum() / n.sum()))


def evaluate(rng, cv, ng=NG, detail=False):
    n, theta, c1, c2 = make(rng, cv, ng=ng)
    cred, k, m, x = credibility(n, c1)
    k_true = 1 / (cv ** 2 * MU)
    z0 = n / (n + k_true); oracle = z0 * x + (1 - z0) * m
    methods = {"その集団の実績そのまま": x, "全体の平均": np.broadcast_to(m, x.shape), "信頼度で混ぜる（重みはデータから）": cred, "信頼度で混ぜる（正しい重み）": oracle}
    out = {"本当の事故率との誤差（人数で重みづけ、RMSE、%ポイント）": {a: round(100 * wrmse(p, theta, n), 4) for a, p in methods.items()},
           "翌年の実績との誤差（人数で重みづけ、RMSE、%ポイント）": {a: round(100 * wrmse(p, c2 / n, n), 4) for a, p in methods.items()},
           "本当の事故率との誤差（集団を同じ重みで、RMSE、%ポイント）": {a: round(100 * float(np.sqrt(((p - theta) ** 2).mean())), 4) for a, p in methods.items()},
           "重みが0.5になる人数（正しい値）": round(k_true, 1),
           "重みが0.5になる人数（データから、中央値）": round(float(np.median(k[np.isfinite(k)])), 1) if np.isfinite(k).any() else None,
           "重みが0.5になる人数（データから、10%点・90%点）": [round(float(q), 1) for q in np.quantile(np.where(np.isfinite(k), k, 1e12), [.1, .9])],
           "集団どうしの差が0と見積もられた割合（%）": round(100 * float((~np.isfinite(k)).mean()), 1)}
    if detail:
        rows = []
        for lo, hi, lab in BINS:
            msk = (n >= lo) & (n < hi)
            r = {"集団の大きさ": lab, "集団の数（1回あたり平均）": round(float(msk.sum(1).mean()), 1), "事故件数の平均（1年）": round(float((n * MU)[msk].mean()), 1)}
            for a, p in methods.items():
                r[a] = round(100 * float(np.sqrt(((p - theta)[msk] ** 2).mean())), 3)
            rows.append(r)
        out["大きさごと"] = rows
        ex = pd.DataFrame({"集団": np.arange(1, ng + 1), "人数": n[0].astype(int), "本当の事故率": theta[0].round(4), "1年目の事故件数": c1[0],
                           "実績の事故率": x[0].round(4), "信頼度で混ぜた事故率": cred[0].round(4), "重み": (n[0] / (n[0] + k[0])).round(3), "2年目の事故件数": c2[0]})
        return out, ex, float(m[0, 0]), float(k[0])
    return out


def main():
    rng = np.random.default_rng(SEED)
    base, ex, m0, k0 = evaluate(rng, 0.3, detail=True)
    ex.to_csv(DATA / "example_100_groups.csv", index=False)
    out = {"設定": {"集団の数": NG, "回数": NSIM, "全体の事故率": MU, "集団の大きさ": "中央値200人の対数正規（10〜20,000人）", "本当の事故率のばらつき（基本、変動係数）": 0.3},
           "基本の場面": base, "例の1回": {"全体の事故率": round(m0, 4), "重みが0.5になる人数": round(k0, 1)}}
    sweep = []
    for cv in (0.1, 0.2, 0.3, 0.5, 0.8):
        e = evaluate(rng, cv)
        sweep.append({"本当の事故率のばらつき（変動係数、%）": int(cv * 100), **{a: v for a, v in e["本当の事故率との誤差（人数で重みづけ、RMSE、%ポイント）"].items()},
                      "重み0.5の人数（正しい値）": e["重みが0.5になる人数（正しい値）"], "重み0.5の人数（データから、中央値）": e["重みが0.5になる人数（データから、中央値）"],
                      "重み0.5の人数（10%点）": e["重みが0.5になる人数（データから、10%点・90%点）"][0], "重み0.5の人数（90%点）": e["重みが0.5になる人数（データから、10%点・90%点）"][1],
                      "差が0と見積もられた割合（%）": e["集団どうしの差が0と見積もられた割合（%）"]})
    sw = pd.DataFrame(sweep); sw.to_csv(RES / "heterogeneity_sweep.csv", index=False)
    few = []
    for ng in (20, 50, 100, 300):
        e = evaluate(rng, 0.3, ng=ng)
        few.append({"集団の数": ng, **e["本当の事故率との誤差（人数で重みづけ、RMSE、%ポイント）"], "重み0.5の人数（データから、中央値）": e["重みが0.5になる人数（データから、中央値）"],
                    "重み0.5の人数（10%点）": e["重みが0.5になる人数（データから、10%点・90%点）"][0], "重み0.5の人数（90%点）": e["重みが0.5になる人数（データから、10%点・90%点）"][1],
                    "差が0と見積もられた割合（%）": e["集団どうしの差が0と見積もられた割合（%）"]})
    fw = pd.DataFrame(few); fw.to_csv(RES / "number_of_groups.csv", index=False)
    pd.DataFrame(base["大きさごと"]).to_csv(RES / "by_size.csv", index=False)
    json.dump(out, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)
    figs(base, sw, ex, k0)
    print(json.dumps(base, ensure_ascii=False, indent=1)); print(sw.to_string()); print(fw.to_string())


def figs(base, sw, ex, k0):
    d = pd.DataFrame(base["大きさごと"]); ms = ["その集団の実績そのまま", "全体の平均", "信頼度で混ぜる（重みはデータから）"]; cs = [BLUE, GRAY, ORANGE]
    fig, ax = plt.subplots(figsize=(9, 4.5)); x = np.arange(len(d))
    for k, (m, c) in enumerate(zip(ms, cs)):
        ax.bar(x + (k - 1) * 0.27, d[m], 0.25, color=c, label=m)
        for xx, y in zip(x + (k - 1) * 0.27, d[m]): ax.text(xx, y + 0.03, f"{y:.2f}", ha="center", fontsize=8.5)
    ax.set_xticks(x); ax.set_xticklabels([f'{a}\n（年{b:.1f}件ほど）' if b < 10 else f'{a}\n（年{b:.0f}件ほど）' for a, b in zip(d["集団の大きさ"], d["事故件数の平均（1年）"])])
    ax.set_ylabel("本当の事故率との誤差（RMSE、%ポイント）"); ax.set_title("集団の大きさごとの誤差（全体の事故率5%、1,000回）"); ax.legend(frameon=False, fontsize=9.5)
    save(fig, "a319_by_size.png", SOURCE, y=-0.04)

    fig, axs = plt.subplots(1, 2, figsize=(10.5, 4.3))
    nn = np.logspace(1, 4.3, 200)
    for cv, c in [(0.1, GRAY), (0.3, ORANGE), (0.8, BLUE)]:
        k = 1 / (cv ** 2 * MU)
        axs[0].plot(nn, nn / (nn + k), color=c, lw=2, label=f"本当の差が{int(cv * 100)}%：{k:,.0f}人で0.5")
        axs[0].plot([k], [0.5], "o", color=c)
    axs[0].axhline(0.5, color=GRAY, lw=.8, ls="--"); axs[0].set_xscale("log"); axs[0].set_xlabel("集団の人数"); axs[0].set_ylabel("その集団の実績にかける重み")
    axs[0].set_title("重みは人数と「本当の差」で決まる", fontsize=12); axs[0].legend(frameon=False, fontsize=9)
    e = ex.sort_values("人数")
    axs[1].scatter(e["人数"], 100 * e["実績の事故率"], s=14, color=BLUE, alpha=.6, label="実績の事故率")
    axs[1].scatter(e["人数"], 100 * e["信頼度で混ぜた事故率"], s=14, color=ORANGE, label="信頼度で混ぜた事故率")
    axs[1].scatter(e["人数"], 100 * e["本当の事故率"], s=10, color=INK, marker="x", label="本当の事故率")
    axs[1].set_xscale("log"); axs[1].set_xlabel("集団の人数"); axs[1].set_ylabel("事故率（%）"); axs[1].set_title("100集団の例（1回分）", fontsize=12); axs[1].legend(frameon=False, fontsize=9)
    save(fig, "a319_weights.png", SOURCE)

    fig, axs = plt.subplots(1, 2, figsize=(10.5, 4.3))
    x = sw["本当の事故率のばらつき（変動係数、%）"]
    for m, c, st in [("その集団の実績そのまま", BLUE, "-o"), ("全体の平均", GRAY, "-o"), ("信頼度で混ぜる（重みはデータから）", ORANGE, "-o"), ("信頼度で混ぜる（正しい重み）", GREEN, "--s")]:
        axs[0].plot(x, sw[m], st, color=c, ms=5, label=m)
    axs[0].set_xlabel("集団どうしの本当の事故率のばらつき（変動係数、%）"); axs[0].set_ylabel("本当の事故率との誤差（RMSE、%ポイント）"); axs[0].set_ylim(0)
    axs[0].set_title("本当の差が大きいほど、平均に寄せると外れる", fontsize=12); axs[0].legend(frameon=False, fontsize=8.5)
    axs[1].fill_between(x, sw["重み0.5の人数（10%点）"], sw["重み0.5の人数（90%点）"].clip(upper=1e5), color=LIGHT, label="データから決めた値（10〜90%）")
    axs[1].plot(x, sw["重み0.5の人数（データから、中央値）"], "-o", color=ORANGE, label="データから決めた値（中央値）")
    axs[1].plot(x, sw["重み0.5の人数（正しい値）"], "--s", color=GREEN, label="正しい値")
    axs[1].set_yscale("log"); axs[1].set_xlabel("集団どうしの本当の事故率のばらつき（変動係数、%）"); axs[1].set_ylabel("重みが0.5になる人数")
    axs[1].set_title("重みを決める人数は、データからどこまで分かるか", fontsize=12); axs[1].legend(frameon=False, fontsize=8.5)
    save(fig, "a319_heterogeneity.png", SOURCE)


if __name__ == "__main__":
    main()

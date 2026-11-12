"""486 損害額の分布を少ない件数で当てはめると、最尤法とモーメント法でどちらが外れやすいのか（架空の損害）"""
import json
import numpy as np
import pandas as pd
from scipy import stats, optimize, special
from common import plt, save, RES, DATA, BLUE, ORANGE, GRAY, INK, GREEN

SEED = 486
NS = [10, 20, 50, 100, 300, 1000]
REPS = 2000
MEAN = 100.0   # 損害額の平均（万円）
BIG = 0.5      # 「大きく外れた」＝正解から±50%以上
SRC = "架空の損害（作成者が乱数で作成、seed 486）"

# ---- 3つの分布（平均はどれも100万円）
def make_truth():
    s = 1.2
    ln = dict(name="対数正規（σ=1.2）", key="lognorm", mu=np.log(MEAN) - s * s / 2, s=s)
    ga = dict(name="ガンマ（形0.7）", key="gamma", k=0.7, th=MEAN / 0.7)
    a = 3.0
    lo = dict(name="パレート型（α=3）", key="lomax", a=a, sc=MEAN * (a - 1))
    for d in (ln, ga, lo):
        d["q99"] = float(quantile(d, 0.99))
    return [ln, ga, lo]


def quantile(d, p):
    if d["key"] == "lognorm":
        return np.exp(d["mu"] + d["s"] * stats.norm.ppf(p))
    if d["key"] == "gamma":
        return stats.gamma.ppf(p, d["k"], scale=d["th"])
    return d["sc"] * ((1 - p) ** (-1 / d["a"]) - 1)


def mean_of(d):
    if d["key"] == "lognorm":
        return np.exp(d["mu"] + d["s"] ** 2 / 2)
    if d["key"] == "gamma":
        return d["k"] * d["th"]
    return d["sc"] / (d["a"] - 1) if d["a"] > 1 else np.inf


def draw(d, n, rng):
    if d["key"] == "lognorm":
        return rng.lognormal(d["mu"], d["s"], n)
    if d["key"] == "gamma":
        return rng.gamma(d["k"], d["th"], n)
    return d["sc"] * ((1 - rng.random(n)) ** (-1 / d["a"]) - 1)


# ---- 2つの当てはめ方（分布の形は正しいものを使う）
def fit_mle(key, x):
    if key == "lognorm":
        lx = np.log(x)
        return dict(key=key, mu=lx.mean(), s=lx.std())          # 最尤法は対数の平均と（n で割る）標準偏差
    if key == "gamma":
        m, lm = x.mean(), np.log(x).mean()
        s = np.log(m) - lm
        k = (3 - s + np.sqrt((s - 3) ** 2 + 24 * s)) / (12 * s)   # 近似の初期値
        for _ in range(30):                                    # ニュートン法で最尤の形を求める
            g = np.log(k) - special.digamma(k) - s
            dg = 1 / k - special.polygamma(1, k)
            k = max(k - g / dg, 1e-4)
        return dict(key=key, k=k, th=m / k)
    # パレート型（Lomax）：尺度ごとに α を式で出し、尺度だけを数値で探す
    def nll(ls):
        sc = np.exp(ls)
        t = np.log1p(x / sc).sum()
        a = len(x) / t
        return -(len(x) * np.log(a / sc) - (a + 1) * t)
    r = optimize.minimize_scalar(nll, bounds=(np.log(x.mean()) - 6, np.log(x.mean()) + 12), method="bounded")
    sc = np.exp(r.x)
    a = len(x) / np.log1p(x / sc).sum()
    return dict(key=key, a=a, sc=sc)


def fit_mom(key, x):
    m, v = x.mean(), x.var(ddof=1)
    cv2 = v / m ** 2
    if key == "lognorm":
        s2 = np.log1p(cv2)
        return dict(key=key, mu=np.log(m) - s2 / 2, s=np.sqrt(s2))
    if key == "gamma":
        k = 1 / cv2
        return dict(key=key, k=k, th=m / k)
    if cv2 <= 1:                       # パレート型は、ばらつきが平均より小さいと当てはめられない
        return None
    a = 2 * cv2 / (cv2 - 1)
    return dict(key=key, a=a, sc=m * (a - 1))


def run():
    rng = np.random.default_rng(SEED)
    truths = make_truth()
    rows, raw20 = [], []
    for d in truths:
        for n in NS:
            em, eq, fails, a_le2 = {"MLE": [], "MOM": []}, {"MLE": [], "MOM": []}, 0, 0
            for r in range(REPS):
                x = draw(d, n, rng)
                for meth, f in (("MLE", fit_mle), ("MOM", fit_mom)):
                    p = f(d["key"], x)
                    if p is None:
                        fails += 1
                        continue
                    if meth == "MLE" and d["key"] == "lomax" and p["a"] <= 2:
                        a_le2 += 1             # 分散が無限大になる形で当てはまった回
                    em[meth].append(mean_of(p) / MEAN - 1)
                    eq[meth].append(quantile(p, 0.99) / d["q99"] - 1)
                    if n == 20:
                        raw20.append(dict(dist=d["name"], method=meth, q99_err=eq[meth][-1]))
            for meth in ("MLE", "MOM"):
                a_m, a_q = np.array(em[meth]), np.array(eq[meth])
                a_m = a_m[np.isfinite(a_m)]
                rows.append(dict(dist=d["name"], key=d["key"], n=n, method=meth, ok=len(a_q),
                                 fail=(fails if meth == "MOM" else 0), mle_a_le2=(a_le2 if meth == "MLE" else 0),
                                 mean_bias=a_m.mean() * 100, mean_rmse=np.sqrt((a_m ** 2).mean()) * 100,
                                 mean_med=np.median(a_m) * 100,
                                 q99_bias=a_q.mean() * 100, q99_med=np.median(a_q) * 100,
                                 q99_rmse=np.sqrt((a_q ** 2).mean()) * 100,
                                 q99_big=(np.abs(a_q) >= BIG).mean() * 100,
                                 q99_low=(a_q <= -BIG).mean() * 100,
                                 q99_high=(a_q >= BIG).mean() * 100))
    T = pd.DataFrame(rows).round(2)
    T.to_csv(RES / "errors_by_n.csv", index=False)
    R20 = pd.DataFrame(raw20)
    R20.to_csv(RES / "q99_errors_n20.csv", index=False, float_format="%.5f")

    # 例のデータ（n=50 の1回分）
    ex = pd.DataFrame({d["key"]: np.round(draw(d, 50, np.random.default_rng(SEED + 1)), 3) for d in truths})
    ex.to_csv(DATA / "example_losses_n50.csv", index=False)

    truth_tbl = pd.DataFrame([dict(dist=d["name"], mean=MEAN, q99=round(d["q99"], 2)) for d in truths])
    truth_tbl.to_csv(RES / "truth.csv", index=False)

    # 図1：99%点の RMSE と件数
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.9), sharey=True)
    for ax, d in zip(axes, truths):
        for meth, col, lab in (("MLE", BLUE, "最尤法"), ("MOM", ORANGE, "モーメント法")):
            s = T[(T.key == d["key"]) & (T.method == meth)]
            ax.plot(s.n, s.q99_rmse, "o-", color=col, label=lab)
        ax.set_xscale("log"); ax.set_xticks(NS); ax.set_xticklabels(NS)
        ax.set_yscale("log"); ax.set_yticks([5, 10, 20, 50, 100, 200, 500]); ax.set_yticklabels([5, 10, 20, 50, 100, 200, 500])
        ax.set_title(d["name"]); ax.set_xlabel("損害の件数")
        ax.grid(alpha=.3)
    axes[0].set_ylabel("99%点の誤差（RMSE、%、対数目盛り）")
    axes[0].legend(frameon=False)
    fig.suptitle("99%点の見積もりの誤差（件数が少ないほど、どちらも大きく外れる）", fontsize=13, y=1.02)
    save(fig, "a486_q99_rmse_by_n.png", SRC + "。正しい分布の形で当てはめ、2,000回くり返した誤差の二乗平均の平方根", y=-0.03)

    # 図2：n=20 の誤差の分布（箱ひげ）
    fig, ax = plt.subplots(figsize=(9.5, 4.2))
    pos, data, cols, labs = [], [], [], []
    for i, d in enumerate(truths):
        for j, (meth, col) in enumerate((("MLE", BLUE), ("MOM", ORANGE))):
            v = R20[(R20.dist == d["name"]) & (R20.method == meth)].q99_err.values * 100
            pos.append(i * 3 + j); data.append(v); cols.append(col)
        labs.append(d["name"])
    bp = ax.boxplot(data, positions=pos, widths=.7, whis=(5, 95), showfliers=False, patch_artist=True, medianprops=dict(color=INK, lw=1.5))
    for b, c in zip(bp["boxes"], cols):
        b.set_facecolor(c); b.set_alpha(.55)
    ax.axhline(0, color=INK, lw=.8); ax.axhspan(-50, 50, color=GRAY, alpha=.12)
    ax.set_xticks([0.5, 3.5, 6.5]); ax.set_xticklabels(labs)
    ax.set_ylabel("99%点の誤差（%）")
    ax.plot([], [], "s", color=BLUE, alpha=.6, label="最尤法"); ax.plot([], [], "s", color=ORANGE, alpha=.6, label="モーメント法")
    ax.legend(frameon=False, loc="upper left")
    ax.set_title("損害20件で当てはめたときの、99%点の誤差の散らばり（灰色は±50%）")
    save(fig, "a486_q99_box_n20.png", SRC + "。箱は25〜75%、ひげは5〜95%の範囲。パレート型のモーメント法は当てはめられなかった回を除く")

    # 図3：大きく外れた回の割合
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.9), sharey=True)
    for ax, d in zip(axes, truths):
        for meth, col, lab, off in (("MLE", BLUE, "最尤法", -0.17), ("MOM", ORANGE, "モーメント法", 0.17)):
            s = T[(T.key == d["key"]) & (T.method == meth)]
            x = np.arange(len(NS)) + off
            ax.bar(x, s.q99_low, 0.32, color=col, alpha=.95, label=lab + "（−50%以下に小さく見積もった）")
            ax.bar(x, s.q99_high, 0.32, bottom=s.q99_low, color=col, alpha=.4, label=lab + "（+50%以上に大きく見積もった）")
        ax.set_xticks(range(len(NS))); ax.set_xticklabels(NS)
        ax.set_title(d["name"]); ax.set_xlabel("損害の件数"); ax.grid(axis="y", alpha=.3)
    axes[0].set_ylabel("99%点が±50%以上外れた回（%）")
    axes[0].legend(frameon=False, fontsize=8)
    fig.suptitle("99%点が正解から±50%以上外れた回の割合", fontsize=13, y=1.02)
    save(fig, "a486_big_miss_share.png", SRC + "。濃い色は−50%以下、薄い色は+50%以上。パレート型のモーメント法は当てはめられた回だけの割合（当てはめられなかった回は件数10で39%）", y=-0.03)

    def g(key, n, meth, col):
        return float(T[(T.key == key) & (T.n == n) & (T.method == meth)][col].iloc[0])
    main = {k: {} for k in ("lognorm", "gamma", "lomax")}
    for key in main:
        for n in NS:
            main[key][n] = {m: {c: g(key, n, m, c) for c in ("q99_rmse", "q99_bias", "q99_med", "q99_big", "q99_low", "q99_high", "mean_rmse", "mean_bias", "fail")} for m in ("MLE", "MOM")}
    main["truth_q99"] = {d["key"]: round(d["q99"], 2) for d in truths}
    main["mle_lomax_a_le2_pct"] = {n: round(g("lomax", n, "MLE", "mle_a_le2") / REPS * 100, 1) for n in NS}
    main["mom_fail_lomax_pct"] = {n: round(g("lomax", n, "MOM", "fail") / REPS * 100, 1) for n in NS}
    json.dump(main, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)
    print(T[["dist", "n", "method", "q99_rmse", "q99_med", "q99_big", "mean_rmse", "fail"]].to_string())


if __name__ == "__main__":
    run()

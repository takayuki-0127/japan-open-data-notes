"""A394 似た変数を2つ入れた回帰は、係数の符号がどれくらい逆になるのか。真の係数（どちらもプラス）が分かっている架空のデータで数える。
python a394_collinearity.py      # 全部を計算し直す（約1〜2分）
"""
import json
import numpy as np, pandas as pd
from scipy import stats
from common import *
SEED = 394
SRC = "出典：架空のデータ（作成者が乱数で作成、seed 394）"
SIGMA = 2.0          # y の揺れ（標準偏差）
RS, NS = (0.0, 0.5, 0.8, 0.9, 0.95, 0.99), (30, 100, 300, 1000)


def draw(rng, n, r, reps):
    x1 = rng.normal(0, 1, (reps, n)); x2 = r * x1 + np.sqrt(1 - r ** 2) * rng.normal(0, 1, (reps, n))
    return x1, x2


def fit2(x1, x2, y):
    """行ごとに y ~ x1 + x2（切片つき）。係数と t 値を返す"""
    n = y.shape[1]; a, b, c = x1 - x1.mean(1, keepdims=True), x2 - x2.mean(1, keepdims=True), y - y.mean(1, keepdims=True)
    s11, s22, s12 = (a * a).sum(1), (b * b).sum(1), (a * b).sum(1); s1y, s2y = (a * c).sum(1), (b * c).sum(1)
    det = s11 * s22 - s12 ** 2; b1 = (s22 * s1y - s12 * s2y) / det; b2 = (s11 * s2y - s12 * s1y) / det
    res = c - b1[:, None] * a - b2[:, None] * b; s2 = (res ** 2).sum(1) / (n - 3)
    se1, se2 = np.sqrt(s2 * s22 / det), np.sqrt(s2 * s11 / det)
    ssr = (c ** 2).sum(1) - (res ** 2).sum(1); F = (ssr / 2) / s2
    return b1, b2, b1 / se1, b2 / se2, stats.f.sf(F, 2, n - 3), y.mean(1) - b1 * x1.mean(1) - b2 * x2.mean(1)


def fit1(x1, y):
    a, c = x1 - x1.mean(1, keepdims=True), y - y.mean(1, keepdims=True); b = (a * c).sum(1) / (a * a).sum(1)
    return b, y.mean(1) - b * x1.mean(1)


def flips(rng, beta=(1.0, 1.0), reps=4000):
    rec = []
    for r in RS:
        for n in NS:
            x1, x2 = draw(rng, n, r, reps); y = beta[0] * x1 + beta[1] * x2 + rng.normal(0, SIGMA, (reps, n))
            b1, b2, t1, t2, pF, _ = fit2(x1, x2, y); tc = stats.t.ppf(0.975, n - 3)
            sd = SIGMA / np.sqrt(n * (1 - r ** 2))                        # 理屈の値（大きな n での係数のばらつき）
            theory = 100 * (stats.norm.cdf(-beta[0] / sd) + stats.norm.cdf(-beta[1] / sd))
            rec.append(dict(beta1=beta[0], beta2=beta[1], r=r, n=n, vif=1 / (1 - r ** 2), any_negative_pct=100 * ((b1 < 0) | (b2 < 0)).mean(),
                            theory_pct=theory, b1_negative_pct=100 * (b1 < 0).mean(), b2_negative_pct=100 * (b2 < 0).mean(),
                            sig_negative_pct=100 * ((t1 < -tc) | (t2 < -tc)).mean(), b1_sd=b1.std(), sum_sd=(b1 + b2).std(), b1_mean=b1.mean(),
                            neither_sig_but_joint_pct=100 * ((np.abs(t1) < tc) & (np.abs(t2) < tc) & (pF < 0.05)).mean()))
    return pd.DataFrame(rec)


def prediction(rng, reps=2000, m=2000):
    """予測の誤差：2つとも入れた式と、x2 を外した式。新しいデータは「同じ相関」と「相関が切れた」の2通り"""
    rec = []
    for r in RS:
        for n in (30, 100, 1000):
            x1, x2 = draw(rng, n, r, reps); y = x1 + x2 + rng.normal(0, SIGMA, (reps, n))
            b1, b2, _, _, _, a2 = fit2(x1, x2, y); c1, a1 = fit1(x1, y)
            for name, rr in (("同じ相関", r), ("相関が切れた（0）", 0.0)):
                u1, u2 = draw(rng, m, rr, reps); t = u1 + u2 + rng.normal(0, SIGMA, (reps, m))
                e2 = t - (a2[:, None] + b1[:, None] * u1 + b2[:, None] * u2); e1 = t - (a1[:, None] + c1[:, None] * u1)
                rec.append(dict(r=r, n=n, new_data=name, rmse_both=np.sqrt((e2 ** 2).mean()), rmse_drop_x2=np.sqrt((e1 ** 2).mean()), noise_sd=SIGMA, b1_when_dropped=c1.mean()))
    return pd.DataFrame(rec)


def figures(fl, pr, ex):
    C = [GRAY, GREEN, BLUE, ORANGE]
    d = fl[fl.beta2 == 1.0]
    fig, ax = plt.subplots(figsize=(9.5, 4.5))
    for c, n in zip(C, NS):
        g = d[d.n == n]; ax.plot(range(len(RS)), g.any_negative_pct, "o-", color=c, label=f"{n:,}件")
        for j, v in enumerate(g.any_negative_pct):
            if v >= 0.5: ax.text(j, v + 1.5, f"{v:.0f}", ha="center", fontsize=9, color=c)
    ax.set_xticks(range(len(RS))); ax.set_xticklabels([f"{r:g}" for r in RS]); ax.set_xlabel("2つの説明変数の相関"); ax.set_ylabel("どちらかの係数がマイナスに出た割合（%）")
    ax.legend(frameon=False, title="データの件数"); ax.set_title("本当はどちらもプラス（1.0）の係数が、マイナスに出た割合（4,000回）")
    save(fig, "a394_sign_flip_rate.png", SRC)
    b1, b2 = ex
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.6))
    ax[0].scatter(b1, b2, s=5, color=BLUE, alpha=0.35); ax[0].axhline(0, color=INK, lw=0.6); ax[0].axvline(0, color=INK, lw=0.6); ax[0].plot([1], [1], "*", color=ORANGE, ms=16, label="本当の値（1.0, 1.0）")
    ax[0].set_xlabel("x1 の係数"); ax[0].set_ylabel("x2 の係数"); ax[0].set_title("係数の組（相関0.95・100件、2,000回）"); ax[0].legend(frameon=False, fontsize=9); ax[0].set_aspect("equal")
    ax[1].hist(b1, bins=50, color=LIGHT, label="x1 の係数"); ax[1].hist(b1 + b2, bins=50, color=ORANGE, alpha=0.8, label="2つの係数の合計")
    ax[1].axvline(1, color=BLUE, lw=1, ls=":"); ax[1].axvline(2, color=ORANGE, lw=1, ls=":"); ax[1].set_xlabel("係数"); ax[1].set_ylabel("回数"); ax[1].set_title("1つずつは大きく揺れるが、合計は揺れない"); ax[1].legend(frameon=False, fontsize=9)
    save(fig, "a394_coefficient_cloud.png", SRC)
    g = pr[(pr.n == 100)]
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.3), sharey=True)
    for a, name in zip(ax, ("同じ相関", "相関が切れた（0）")):
        h = g[g.new_data == name]; x = np.arange(len(RS))
        a.bar(x - 0.2, h.rmse_both, 0.4, color=BLUE, label="2つとも入れた式"); a.bar(x + 0.2, h.rmse_drop_x2, 0.4, color=ORANGE, label="片方（x2）を外した式")
        for i, (p, q) in enumerate(zip(h.rmse_both, h.rmse_drop_x2)): a.text(i - 0.2, p + 0.02, f"{p:.2f}", ha="center", fontsize=8); a.text(i + 0.2, q + 0.02, f"{q:.2f}", ha="center", fontsize=8)
        a.axhline(SIGMA, color=INK, lw=0.6, ls=":"); a.set_xticks(x); a.set_xticklabels([f"{r:g}" for r in RS]); a.set_xlabel("作ったときの2つの変数の相関"); a.set_title("新しいデータ：" + name); a.set_ylim(1.8, 3.0)
    ax[0].set_ylabel("予測の誤差（RMSE。点線＝これ以上は下がらない2.0）"); ax[0].legend(frameon=False, fontsize=9)
    fig.suptitle("予測の誤差（100件で作った式）：相関が同じならどちらも変わらない。相関が切れると、どちらの式も外れる", y=1.02)
    save(fig, "a394_prediction_error.png", SRC)


if __name__ == "__main__":
    rng = np.random.default_rng(SEED)
    fl = pd.concat([flips(rng), flips(rng, (1.0, 0.3))]); pr = prediction(rng)
    x1, x2 = draw(rng, 100, 0.95, 2000); y = x1 + x2 + rng.normal(0, SIGMA, (2000, 100)); b1, b2, t1, t2, pF, _ = fit2(x1, x2, y)
    fl.round(4).to_csv(RES / "sign_flips.csv", index=False); pr.round(4).to_csv(RES / "prediction.csv", index=False)
    pd.DataFrame({"b1": b1, "b2": b2, "t1": t1, "t2": t2, "p_joint": pF}).round(4).to_csv(RES / "coefficients_r095_n100.csv", index=False)
    pd.DataFrame({"x1": x1[0], "x2": x2[0], "y": y[0]}).round(4).to_csv(DATA / "example_r095_n100.csv", index=False)
    figures(fl, pr, (b1, b2))
    main = {"seed": SEED, "sigma": SIGMA, "flips_equal": fl[fl.beta2 == 1.0].round(2).to_dict("records"), "flips_unequal": fl[fl.beta2 == 0.3].round(2).to_dict("records"),
            "prediction": pr.round(3).to_dict("records"),
            "cloud_r095_n100": {"any_negative_pct": round(100 * float(((b1 < 0) | (b2 < 0)).mean()), 1), "corr_b1_b2": round(float(np.corrcoef(b1, b2)[0, 1]), 3),
                                "b1_sd": round(float(b1.std()), 3), "sum_sd": round(float((b1 + b2).std()), 3), "b1_range": [round(float(b1.min()), 2), round(float(b1.max()), 2)]}}
    json.dump(main, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)
    c = ["r", "n", "any_negative_pct", "theory_pct", "sig_negative_pct", "b1_sd", "sum_sd", "neither_sig_but_joint_pct"]
    print(fl[fl.beta2 == 1.0][c].round(2).to_string()); print(fl[fl.beta2 == 0.3][["r", "n", "any_negative_pct", "b2_negative_pct", "sig_negative_pct"]].round(2).to_string())
    print(pr.round(3).to_string()); print(main["cloud_r095_n100"])

"""538 0か1かの結果を線形回帰で当てると、確率が0〜1をはみ出す割合と、効果の推定はどれだけずれるのか（統計・回帰）

架空の会員データ：「キャンペーンの案内を送ったか」D（無作為に半分）と、利用の多さ x（標準化した値）から、
申し込んだか y（0/1）が決まる。本当の仕組みはロジスティック：logit P(y=1) = a + 0.5·D + c·x。
- x の効き方 c：0.5・1.0・2.0
- 全体の申し込み率：およそ 5%・20%・50%（a を調整）
- 会員 5,000人、各場面 200回（乱数の種 538）
線形確率モデル（y を D と x で最小二乗）とロジスティック回帰（ニュートン法）を当て、
予測が0〜1をはみ出す割合、案内の平均の効果（申し込み率の差、ポイント）、x の上下1割の層での効果を比べる。
"""
import json
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import FIG, RES, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SRC = "架空の会員の申し込みデータ（作成者が乱数で作成、seed 538）"
N = 5_000
REPS = 200
B = 0.5
CS = [0.5, 1.0, 2.0]
RATES = [0.05, 0.20, 0.50]
sig = lambda z: 1 / (1 + np.exp(-z))


def solve_a(c, rate):
    zg = np.random.default_rng(0).normal(size=200_000)
    lo, hi = -12.0, 12.0
    for _ in range(80):
        mid = (lo + hi) / 2
        m = 0.5 * (sig(mid + c * zg) + sig(mid + B + c * zg)).mean()
        lo, hi = (mid, hi) if m < rate else (lo, mid)
    return (lo + hi) / 2


def logit_fit(X, y):
    beta = np.zeros(X.shape[1])
    for _ in range(50):
        p = sig(X @ beta)
        g = X.T @ (y - p)
        H = (X * (p * (1 - p))[:, None]).T @ X
        step = np.linalg.solve(H, g)
        beta += step
        if np.abs(step).max() < 1e-10:
            break
    return beta


def main():
    rng = np.random.default_rng(538)
    rows, curves = [], []
    for c in CS:
        for rate in RATES:
            a = solve_a(c, rate)
            for r in range(REPS):
                x = rng.normal(size=N)
                d = (rng.random(N) < 0.5).astype(float)
                y = (rng.random(N) < sig(a + B * d + c * x)).astype(float)
                X = np.column_stack([np.ones(N), d, x])
                bl = np.linalg.lstsq(X, y, rcond=None)[0]
                pl = X @ bl
                bg = logit_fit(X, y)
                X1, X0 = X.copy(), X.copy(); X1[:, 1] = 1; X0[:, 1] = 0
                true_eff = sig(a + B + c * x) - sig(a + c * x)
                logit_eff = sig(X1 @ bg) - sig(X0 @ bg)
                lo, hi = x <= np.quantile(x, 0.1), x >= np.quantile(x, 0.9)
                rows.append(dict(c=c, rate=rate, a=a, rep=r, y_mean=y.mean(),
                                 out_share=float(((pl < 0) | (pl > 1)).mean()), below0=float((pl < 0).mean()), above1=float((pl > 1).mean()),
                                 true_ame=true_eff.mean() * 100, lpm_ame=bl[1] * 100, logit_ame=logit_eff.mean() * 100,
                                 true_lo=true_eff[lo].mean() * 100, logit_lo=logit_eff[lo].mean() * 100,
                                 true_hi=true_eff[hi].mean() * 100, logit_hi=logit_eff[hi].mean() * 100))
                if rate == 0.20 and c == 1.0:
                    dec = pd.qcut(x, 10, labels=False)
                    for k in range(10):
                        m = dec == k
                        curves.append(dict(rep=r, decile=k + 1, x_mid=float(np.median(x[m])), true=true_eff[m].mean() * 100,
                                           logit=logit_eff[m].mean() * 100, lpm=bl[1] * 100))
    df = pd.DataFrame(rows)
    df.to_csv(RES / "reps.csv", index=False, float_format="%.6f")
    sm = df.groupby(["c", "rate"]).mean(numeric_only=True).drop(columns="rep").reset_index()
    sm["lpm_minus_true_ame"] = sm.lpm_ame - sm.true_ame
    sm["logit_minus_true_ame"] = sm.logit_ame - sm.true_ame
    sm["lpm_minus_true_lo"] = sm.lpm_ame - sm.true_lo
    sm["lpm_minus_true_hi"] = sm.lpm_ame - sm.true_hi
    sm.to_csv(RES / "summary.csv", index=False, float_format="%.6f")
    cv = pd.DataFrame(curves).groupby("decile").mean(numeric_only=True).drop(columns="rep").reset_index(); cv.to_csv(RES / "decile_curve.csv", index=False, float_format="%.6f")
    json.dump({"rows": sm.round(6).to_dict("records")}, open(RES / "a538_main.json", "w"), ensure_ascii=False, indent=1)

    # 図1：はみ出す割合
    fig, ax = plt.subplots(figsize=(7.5, 4))
    xx = np.arange(len(RATES)); w = 0.26
    for i, (c, col) in enumerate(zip(CS, [LIGHT, BLUE, INK])):
        t = sm[sm.c == c].sort_values("rate")
        ax.bar(xx + (i - 1) * w, t.out_share * 100, w, color=col, label=f"x の効き方 c={c}")
        for xi, v in zip(xx + (i - 1) * w, t.out_share * 100):
            ax.text(xi, v + 0.4, f"{v:.1f}", ha="center", fontsize=8)
    ax.set_xticks(xx); ax.set_xticklabels([f"申し込み率 約{int(r*100)}%" for r in RATES])
    ax.set_ylabel("予測が0未満か1超の割合（%）")
    ax.legend(fontsize=8, frameon=False)
    ax.set_title("線形回帰の予測が0〜1をはみ出す割合")
    save(fig, "a538_out_of_range.png", SRC + "。200回の平均")

    # 図2：平均の効果
    fig, ax = plt.subplots(figsize=(8, 4))
    lab = [f"c={c}\n約{int(r*100)}%" for c in CS for r in RATES]
    t = sm.sort_values(["c", "rate"])
    xx = np.arange(len(t))
    ax.plot(xx, t.true_ame, "o", color=INK, ms=8, label="本当の平均の効果")
    ax.plot(xx, t.lpm_ame, "s", color=ORANGE, label="線形確率モデルの係数")
    ax.plot(xx, t.logit_ame, "^", color=BLUE, label="ロジスティックの平均の効果")
    ax.set_xticks(xx); ax.set_xticklabels(lab, fontsize=8)
    ax.set_ylabel("案内による申し込み率の差（ポイント）")
    ax.legend(fontsize=8, frameon=False)
    ax.set_title("平均の効果は、線形でもロジスティックでもほぼ同じ")
    save(fig, "a538_ame.png", SRC + "。200回の平均。下の段は x の効き方と全体の申し込み率")

    # 図3：層ごとの効果
    fig, ax = plt.subplots(figsize=(7.5, 4))
    ax.plot(cv.decile, cv.true, "o-", color=INK, label="本当の効果")
    ax.plot(cv.decile, cv.logit, "^--", color=BLUE, label="ロジスティック")
    ax.plot(cv.decile, cv.lpm, "-", color=ORANGE, lw=2, label="線形確率モデル（どの層も同じ）")
    ax.set_xticks(range(1, 11)); ax.set_xlabel("利用の多さ x の十分位（1 = 少ない）")
    ax.set_ylabel("案内による申し込み率の差（ポイント）")
    ax.legend(fontsize=8, frameon=False)
    ax.set_title("端の層では、線形の「一律の効果」と本当の効果が離れる（c=1・約20%）")
    save(fig, "a538_effect_by_decile.png", SRC + "。200回の平均")
    print(sm.round(3).to_string()); print(cv.round(2).to_string())


if __name__ == "__main__":
    main()

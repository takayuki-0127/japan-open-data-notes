"""518 支払いに何年もかかる損害は、利率で割り引くと、払い方の遅さによってどれだけ小さくなるのか（保険数理・リスク）

架空の支払いパターン。損害100（割り引かない額）を、ガンマ分布（形 2）の形で何年かに分けて払う。
平均の支払い時期 m = 0.5・1・2・4・8・15年。j 年目（0始まり）の支払いは年の真ん中（j+0.5年）に払うと置く。
今の価値（現在価値）= Σ 支払い_j ÷ (1+r)^(j+0.5)。r = 0〜5%。乱数は使わない。
"""
import json
import numpy as np, pandas as pd
from scipy.stats import gamma
import matplotlib.pyplot as plt
from common import FIG, RES, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SRC = "架空の支払いパターン（作成者が置いた値、乱数は使わない）"
MS = [0.5, 1, 2, 4, 8, 15]
RATES = np.round(np.arange(0, 0.0501, 0.0025), 4)
H = 80   # 80年で打ち切り（残りは最後の年に払う）


def pattern(m, shape=2.0, delay=0):
    j = np.arange(H + 1)
    # ガンマ分布を1年ごとに区切り、その年の分を年の真ん中に払う（平均の支払い時期はおおよそ m）
    F = gamma.cdf(j, shape, scale=m / shape)
    w = np.diff(F); w[-1] += 1 - F[-1]
    if delay:
        w = np.concatenate([np.zeros(delay), w[:-delay]]); w[-1] += 1 - w.sum()
    return w   # 長さ H、j=0..H-1


def pv(w, r):
    t = np.arange(len(w)) + 0.5
    return float((w / (1 + r) ** t).sum())


def main():
    rows = []
    for m in MS:
        w = pattern(m); wd = pattern(m, delay=1)
        mean_t = float((w * (np.arange(H) + 0.5)).sum())
        for r in RATES:
            rows.append(dict(m=m, mean_time=round(mean_t, 3), rate=r, pv_ratio=round(pv(w, r), 5), pv_ratio_delay1=round(pv(wd, r), 5)))
    df = pd.DataFrame(rows); df.to_csv(RES / "pv_grid.csv", index=False)
    g = lambda m, r, c="pv_ratio": float(df[(df.m == m) & (np.isclose(df.rate, r))][c].iloc[0])
    summ = []
    for m in MS:
        w = pattern(m)
        summ.append(dict(m=m, mean_time=round(float((w * (np.arange(H) + 0.5)).sum()), 3),
                         paid_in_1y=round(float(w[:1].sum()), 4), paid_in_5y=round(float(w[:5].sum()), 4),
                         pv_1pct=round(g(m, 0.01), 4), pv_2pct=round(g(m, 0.02), 4), pv_4pct=round(g(m, 0.04), 4),
                         rate_up_1pt_from_2pct=round(g(m, 0.03) / g(m, 0.02) - 1, 4),
                         rate_down_1pt_from_2pct=round(g(m, 0.01) / g(m, 0.02) - 1, 4),
                         delay1y_at_2pct=round(g(m, 0.02, "pv_ratio_delay1") / g(m, 0.02) - 1, 4),
                         rate_up_1pt_from_0=round(g(m, 0.01) / g(m, 0.0) - 1, 4)))
    sm = pd.DataFrame(summ); sm.to_csv(RES / "summary.csv", index=False)
    json.dump(dict(shape=2.0, horizon=H, mid_year=True, summary=sm.to_dict("records")), open(RES / "a518_main.json", "w"), ensure_ascii=False, indent=1)
    print(sm.to_string())

    # 図1：払い方（累積）
    fig, ax = plt.subplots(figsize=(7.6, 4.4)); cols = [LIGHT, GREEN, BLUE, ORANGE, INK, GRAY]
    for m, c in zip(MS, cols):
        ax.plot(np.arange(1, 41), np.cumsum(pattern(m))[:40] * 100, color=c, lw=2.2, label=f"平均{m:g}年で払う")
    ax.set_xlabel("年（その年の終わりまで）"); ax.set_ylabel("払い終えた割合（%）"); ax.set_ylim(0, 102)
    ax.set_title("6つの払い方：同じ損害100を、平均0.5年〜15年かけて払う")
    ax.legend(frameon=False, fontsize=9, ncol=2)
    save(fig, "a518_patterns.png", SRC + "。ガンマ分布（形2）の形で年ごとに払う")

    # 図2：利率と今の価値
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    for m, c in zip(MS, cols):
        x = df[df.m == m]; ax.plot(x.rate * 100, x.pv_ratio * 100, color=c, lw=2.2, label=f"平均{m:g}年")
        ax.annotate(f"{x.pv_ratio.iloc[-1]*100:.0f}", (5, x.pv_ratio.iloc[-1] * 100), textcoords="offset points", xytext=(5, -3), fontsize=9, color=c if c != LIGHT else BLUE)
    ax.set_xlabel("利率（%／年）"); ax.set_ylabel("今の価値（割り引かない額＝100）"); ax.set_xlim(0, 5.5)
    ax.set_title("払うのが遅いほど、利率で割り引いた額は小さくなる")
    ax.legend(frameon=False, fontsize=9, ncol=2, loc="lower left")
    save(fig, "a518_pv_by_rate.png", SRC + "。支払いは年の真ん中と置いた")

    # 図3：利率+1ポイントと1年遅れ
    fig, ax = plt.subplots(figsize=(7.6, 4.4)); xs = np.arange(len(MS)); w = 0.38
    a = sm.rate_up_1pt_from_2pct * 100; b = sm.delay1y_at_2pct * 100
    ax.bar(xs - w / 2, a, w, color=BLUE, label="利率が2%→3%になると")
    ax.bar(xs + w / 2, b, w, color=ORANGE, label="支払いがどれも1年遅れると（利率2%）")
    for x, v in zip(xs - w / 2, a): ax.text(x, v - 0.3, f"{v:.1f}", ha="center", va="top", fontsize=8.5, color=INK)
    for x, v in zip(xs + w / 2, b): ax.text(x, v - 0.3, f"{v:.1f}", ha="center", va="top", fontsize=8.5, color=INK)
    ax.axhline(0, color=INK, lw=0.8); ax.set_xticks(xs, [f"平均{m:g}年" for m in MS])
    ax.set_ylabel("今の価値の変化（%）"); ax.set_ylim(-13, 0.5)
    ax.set_title("利率1ポイントの影響は払い方の遅さで大きく変わり、1年遅れはどれも約2%")
    ax.legend(frameon=False, fontsize=9, loc="lower left")
    save(fig, "a518_sensitivity.png", SRC)


if __name__ == "__main__":
    main()

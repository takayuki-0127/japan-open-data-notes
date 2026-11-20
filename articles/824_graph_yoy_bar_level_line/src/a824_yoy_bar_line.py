"""824 「前年比」の棒と「実数」の線を並べると、何を読み違えるのか？（架空のデータ）

架空の会社2,000社の月の売上（48か月）。本当の伸び（作成者が置いた答え）に、
季節の波と月ごとのばらつきを足して作る。13か月目からの前年同月比（棒）と売上（線）を並べたとき、
棒と線の動きが、本当の伸びとどれだけ食い違って見えるかを数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 824
SRC = "架空の会社の月の売上（作成者が乱数で作成、seed 824）"
N_CO, T = 2000, 48
BASE = dict(growth=0.05, sd=0.05, ar=0.0, amp=0.15)


def make(rng, n=N_CO, growth=0.05, sd=0.05, ar=0.0, amp=0.15, slowdown=False):
    """growth：1年の本当の伸び（対数）。slowdown=True なら 1年+10% から 0% まで直線で下げる"""
    t = np.arange(T)
    if slowdown:
        g_month = (0.10 - 0.10 * t / (T - 1)) / 12
    else:
        g_month = np.full(T, growth / 12)
    G = np.cumsum(g_month) - g_month[0]
    ph = rng.uniform(0, 2 * np.pi, n)
    season = 1 + amp * np.sin(2 * np.pi * t[None, :] / 12 + ph[:, None])
    # 月ごとのばらつき：1次の自己相関 ar、標準偏差 sd（定常）
    z = rng.normal(size=(n, T))
    e = np.empty((n, T))
    e[:, 0] = z[:, 0] * sd
    for k in range(1, T):
        e[:, k] = ar * e[:, k - 1] + np.sqrt(1 - ar ** 2) * sd * z[:, k]
    level = 100 * np.exp(G)[None, :] * season
    return level * np.exp(e), level


def yoy(s):
    return s[:, 12:] / s[:, :-12] - 1  # 13〜48か月目の36本


def longest_fall_run(d):
    """前の月より下がった（d<0）が続く最長の長さ（行ごと）"""
    best = np.zeros(d.shape[0], int); cur = np.zeros(d.shape[0], int)
    for k in range(d.shape[1]):
        cur = np.where(d[:, k] < 0, cur + 1, 0)
        best = np.maximum(best, cur)
    return best


def measures(s, true_yoy):
    y = yoy(s)
    dy = np.diff(y, axis=1)
    # 1年（12本）ごとに、3か月以上続けて棒が下がる並びがあるか
    run3 = np.mean([np.mean(longest_fall_run(dy[:, 12 * j:12 * j + 11]) >= 3) for j in range(3)])
    # 前年の反動：同じ月の前年の棒との相関（25〜48か月目の24本）
    a, b = y[:, 12:].ravel(), y[:, :-12].ravel()
    low = b <= np.quantile(b, .25)
    # 線（売上）が前の月より下がった月のうち、棒（前年比）はプラスだった割合
    ds = np.diff(s[:, 12:], axis=1)
    line_down = ds < 0
    bar_pos = y[:, 1:] > 0
    return {"true_yoy_pct": round(float(true_yoy) * 100, 2),
            "bar_mean_pct": round(float(y.mean()) * 100, 2),
            "bar_p10_pct": round(float(np.quantile(y, .1)) * 100, 2), "bar_p90_pct": round(float(np.quantile(y, .9)) * 100, 2),
            "bar_negative_share": round(float((y < 0).mean()), 3),
            "bar_down_from_prev_share": round(float((dy < 0).mean()), 3),
            "year_with_3month_fall_share": round(float(run3), 3),
            "corr_with_same_month_last_year": round(float(np.corrcoef(a, b)[0, 1]), 3),
            "after_low_bar_next_year_above_median": round(float((a[low] > np.median(a)).mean()), 3),
            "line_down_share": round(float(line_down.mean()), 3),
            "line_down_but_bar_positive_share": round(float((line_down & bar_pos).sum() / line_down.sum()), 3)}


def main():
    rng = np.random.default_rng(SEED)
    s, lv = make(rng, **BASE)
    true_yoy = np.exp(BASE["growth"]) - 1
    base = measures(s, true_yoy)

    # data：全社の月の売上と前年同月比
    df = pd.DataFrame({"company_id": np.repeat(np.arange(1, N_CO + 1), T), "month": np.tile(np.arange(1, T + 1), N_CO),
                       "sales": s.ravel().round(2)})
    yy = np.full((N_CO, T), np.nan); yy[:, 12:] = yoy(s)
    df["yoy_pct"] = (yy.ravel() * 100).round(2)
    df.to_csv(DATA / "companies_monthly.csv", index=False)

    # 伸びの鈍化：1年+10%から0%へ（本当の売上は最後まで増え続ける）
    s2, lv2 = make(np.random.default_rng(SEED + 1), slowdown=True)
    y2 = yoy(s2)
    tt = np.arange(y2.shape[1]) - (y2.shape[1] - 1) / 2
    bar_slope_neg = (y2 * tt).sum(1) < 0
    last_up = s2[:, 36:].sum(1) > s2[:, 24:36].sum(1)
    true_y2 = yoy(lv2)
    slow = {"true_yoy_first_bar_pct": round(float(true_y2[0, 0]) * 100, 2),
            "true_yoy_last_bar_pct": round(float(true_y2[0, -1]) * 100, 2),
            "bars_trend_down_share": round(float(bar_slope_neg.mean()), 3),
            "last_year_total_up_share": round(float(last_up.mean()), 3),
            "both_share": round(float((bar_slope_neg & last_up).mean()), 3),
            "last_year_bar_negative_share": round(float((y2[:, 24:] < 0).mean()), 3),
            "true_last_year_bar_negative_share": round(float((true_y2[:, 24:] < 0).mean()), 3)}

    # 確かめ：ばらつき・自己相関・季節・本当の伸びを変える
    sens = []
    variants = [("基本（伸び5%・ばらつき5%・自己相関0・季節15%）", {}),
                ("ばらつき2%", {"sd": 0.02}), ("ばらつき10%", {"sd": 0.10}),
                ("自己相関0.5", {"ar": 0.5}), ("自己相関0.9", {"ar": 0.9}),
                ("季節の波0%", {"amp": 0.0}), ("季節の波30%", {"amp": 0.30}),
                ("本当の伸び0%", {"growth": 0.0}), ("本当の伸び10%", {"growth": 0.10})]
    for j, (name, ch) in enumerate(variants):
        kw = dict(BASE, **ch)
        ss = s if j == 0 else make(np.random.default_rng(SEED * 10 + j), **kw)[0]
        r = measures(ss, np.exp(kw["growth"]) - 1)
        r["variant"] = name
        sens.append(r)
    pd.DataFrame(sens).to_csv(RES / "sensitivity.csv", index=False)

    out = {"constant_growth_base": base, "slowdown_10_to_0": slow, "sensitivity": sens}
    json.dump(out, open(RES / "a824_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：伸びの鈍化の会社の例（棒＝前年比、線＝売上、2本の縦軸）
    # 例：棒も線も条件を満たす会社のうち、棒の下がり方が上から1割の位置の会社（はっきりした例を選んだ）
    slope = (y2 * tt).sum(1) / (tt ** 2).sum() * 12 * 100   # 1年あたり何ポイント下がるか
    ok = np.where(bar_slope_neg & last_up)[0]
    e = int(ok[np.argsort(slope[ok])[len(ok) // 10]])
    m = np.arange(13, T + 1)
    fig, ax = plt.subplots(figsize=(8.4, 4.2))
    yv = y2[e] * 100
    ax.bar(m, yv, color=[LIGHT if v >= 0 else GRAY for v in yv], width=.75)
    ax.bar([np.nan], [np.nan], color=LIGHT, label="前年同月比（左の目盛り、マイナスは灰色）")
    ax.plot(m, true_y2[e] * 100, color=BLUE, lw=1.2, ls="--", label="本当の伸び（作成者が置いた値）")
    ax.axhline(0, color=INK, lw=.6)
    ax.set_ylabel("前年同月比（%）"); ax.set_xlabel("月")
    ax2 = ax.twinx()
    ax2.plot(m, s2[e, 12:], color=ORANGE, lw=1.8, marker="o", ms=2.5, label="売上（右の目盛り）")
    ax2.set_ylabel("売上（架空の単位）", color=ORANGE)
    ax2.spines["right"].set_visible(True); ax2.spines["top"].set_visible(False)
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, frameon=False, fontsize=8.5, ncol=3, loc="upper center", bbox_to_anchor=(.5, -.14))
    ax.set_title(f"棒は右下がりでも、最後の12か月の売上はその前の12か月より{(s2[e,36:].sum()/s2[e,24:36].sum()-1)*100:.0f}%多い\n（{e+1}社目、本当の伸びは+10%から0%へ鈍るが、売上は増え続ける）",
                 fontsize=11)
    save(fig, "a824_example.png", SRC, y=-0.1)
    out["figure_example"] = {"company_id": e + 1,
                             "last_year_vs_prev_pct": round(float(s2[e, 36:].sum() / s2[e, 24:36].sum() - 1) * 100, 1),
                             "bar_slope_pt_per_year": round(float(slope[e]), 2),
                             "median_bar_slope_pt_per_year_all": round(float(np.median(slope)), 2)}
    json.dump(out, open(RES / "a824_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図2：本当の伸び+5%一定でも、棒はこれだけ散らばる（ばらつき別）
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    bins = np.linspace(-30, 40, 71)
    for j, (sd, col) in enumerate([(0.02, BLUE), (0.05, ORANGE), (0.10, GRAY)]):
        ss = s if sd == 0.05 else make(np.random.default_rng(SEED * 10 + (1 if sd == 0.02 else 2)), **dict(BASE, sd=sd))[0]
        ax.hist(yoy(ss).ravel() * 100, bins=bins, density=True, histtype="step", lw=1.8, color=col,
                label=f"月ごとのばらつき{int(sd*100)}%")
    ax.axvline(true_yoy * 100, color=INK, lw=1, ls="--")
    ax.text(true_yoy * 100 - .8, ax.get_ylim()[1] * .92, f"本当の伸び +{true_yoy*100:.1f}%", fontsize=9, ha="right")
    ax.axvline(0, color=GRAY, lw=.6)
    ax.set_yticks([]); ax.set_xlabel("前年同月比の棒の高さ（%）")
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    ax.set_title("本当の伸びが毎月+5%でも、前年同月比の棒は上下に散らばる")
    save(fig, "a824_spread.png", SRC, y=-0.05)

    # 図3：前年の反動（前年の同じ月の棒と、今年の棒）
    y = yoy(s)
    a, b = y[:, 12:].ravel() * 100, y[:, :-12].ravel() * 100
    pick = np.random.default_rng(SEED + 7).choice(len(a), 4000, replace=False)
    fig, ax = plt.subplots(figsize=(6.4, 4.4))
    ax.scatter(b[pick], a[pick], s=5, color=BLUE, alpha=.35, lw=0)
    ax.axhline(true_yoy * 100, color=INK, lw=.8, ls="--"); ax.axvline(true_yoy * 100, color=INK, lw=.8, ls="--")
    ax.set_xlabel("前の年の同じ月の前年同月比（%）"); ax.set_ylabel("今年の前年同月比（%）")
    ax.set_title(f"前の年に低かった月は、翌年高く出る（相関 {base['corr_with_same_month_last_year']:.2f}）", fontsize=11.5)
    save(fig, "a824_rebound.png", SRC, y=-0.03)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()

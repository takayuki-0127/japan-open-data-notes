"""820 対数の軸と普通の軸で、「伸びが鈍った」の見え方は？（架空のデータ）

架空の会社の毎月の会員数（60か月）。36か月目から伸び率（前の月からの増え方の%）を r1 から r2 に変える。
「伸びが鈍った」かどうかを、普通の軸（会員数そのまま）と対数の軸（会員数の対数）で、
変わる前の12か月と最後の12か月の傾きを比べて判断し、本当の伸び率の変化と合うかを数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
COMMA = FuncFormatter(lambda v, _: f"{v:,.0f}")
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 820
SRC = "架空の会社の会員数（作成者が乱数で作成、seed 820）"
N_MONTH, CHANGE = 60, 36
START = 1000
NOISE = 0.02                       # 毎月の上下（掛け算、標準偏差2%）
BEFORE = np.arange(24, 36)         # 変わる前の12か月
AFTER = np.arange(48, 60)          # 最後の12か月
AFTER_EARLY = np.arange(36, 48)    # 確かめ：変わった直後の12か月
R1S = [0.02, 0.03, 0.04, 0.05, 0.06]
N_REP = 200


def path(r1, r2):
    t = np.arange(N_MONTH)
    lr = np.where(t < CHANGE, np.log1p(r1), np.log1p(r2))
    lr[0] = 0
    return START * np.exp(np.cumsum(lr))


def slope(y, idx):
    x = idx - idx.mean()
    return float((x * (y[idx] - y[idx].mean())).sum() / (x ** 2).sum())


def judge(y, after=AFTER):
    """傾きの比（後÷前）。1より小さければ「鈍った」と読む"""
    lin = slope(y, after) / slope(y, BEFORE)
    lg = slope(np.log(y), after) / slope(np.log(y), BEFORE)
    return lin, lg


def main():
    rng = np.random.default_rng(SEED)

    # 1) 例：伸び率 4% → 3%
    y_true = path(0.04, 0.03)
    y = y_true * np.exp(rng.normal(0, NOISE, N_MONTH))
    lin, lg = judge(y)
    lin0, lg0 = judge(y_true)
    pd.DataFrame({"month": np.arange(N_MONTH), "true": np.round(y_true, 1), "members": np.round(y).astype(int)}) \
        .to_csv(DATA / "members_4to3.csv", index=False)
    ex = {"r1": 0.04, "r2": 0.03, "lin_ratio": round(lin, 3), "log_ratio": round(lg, 3),
          "lin_ratio_no_noise": round(lin0, 3), "log_ratio_no_noise": round(lg0, 3),
          "inc_before_per_month": round(slope(y_true, BEFORE), 1), "inc_after_per_month": round(slope(y_true, AFTER), 1),
          "members_m0": int(round(y[0])), "members_m35": int(round(y[35])), "members_m59": int(round(y[59]))}

    # 2) 伸び率の組み合わせごとに「鈍った」と読む割合（200回）
    rows = []
    for r1 in R1S:
        for r2 in np.round(np.arange(0, r1 + 0.0101, 0.005), 3):
            yt = path(r1, r2)
            ys = yt[None, :] * np.exp(np.random.default_rng(SEED * 1000 + int(r1 * 1000) * 100 + int(r2 * 1000))
                                      .normal(0, NOISE, (N_REP, N_MONTH)))
            j = np.array([judge(v) for v in ys])
            je = np.array([judge(v, AFTER_EARLY) for v in ys])
            rows.append({"r1": r1, "r2": r2, "rate_slowed": bool(r2 < r1),
                         "lin_slowed_share": round(float((j[:, 0] < 1).mean()), 3),
                         "log_slowed_share": round(float((j[:, 1] < 1).mean()), 3),
                         "lin_ratio_true": round(judge(yt)[0], 3), "log_ratio_true": round(judge(yt)[1], 3),
                         "lin_slowed_share_early": round(float((je[:, 0] < 1).mean()), 3),
                         "log_slowed_share_early": round(float((je[:, 1] < 1).mean()), 3)})
    grid = pd.DataFrame(rows)
    grid.to_csv(RES / "grid.csv", index=False)
    sl = grid[grid.rate_slowed]
    # 普通の軸で「鈍った」と読めなくなる r2（伸び率がこれより上なら、普通の軸では速まって見える）
    border = {}
    for r1 in R1S:
        g = grid[(grid.r1 == r1)]
        ok = g[g.lin_ratio_true < 1]
        border[str(r1)] = float(ok.r2.max()) if len(ok) else None
    one_pt = grid[np.isclose(grid.r2, grid.r1 - 0.01)].set_index("r1")
    summ = {"lin_border_r2_by_r1_no_noise": border,
            "r2_eq_r1_minus_1pt": {str(k): {"lin": float(v.lin_slowed_share), "log": float(v.log_slowed_share),
                                           "lin_early": float(v.lin_slowed_share_early)}
                                   for k, v in one_pt.iterrows()},
            "no_change_log_slowed_mean": round(float(grid[np.isclose(grid.r1, grid.r2)].log_slowed_share.mean()), 3),
            "no_change_lin_slowed_mean": round(float(grid[np.isclose(grid.r1, grid.r2)].lin_slowed_share.mean()), 3)}

    # 2b) 確かめ：毎月の上下の大きさ（r1=4%）
    sens = {}
    for nz in [0.01, 0.02, 0.04]:
        d = {}
        for r2 in [0.02, 0.03, 0.035, 0.04]:
            ys = path(0.04, r2)[None, :] * np.exp(np.random.default_rng(SEED * 7 + int(nz * 1000) * 100 + int(r2 * 1000))
                                                  .normal(0, nz, (N_REP, N_MONTH)))
            j = np.array([judge(v) for v in ys])
            d[str(r2)] = {"lin": round(float((j[:, 0] < 1).mean()), 3), "log": round(float((j[:, 1] < 1).mean()), 3)}
        sens[str(nz)] = d
    summ["noise_sens_r1_4pct"] = sens

    # 3) 毎月同じ人数ずつ増える会社（増える数は一定、伸び率は下がり続ける）
    inc = 40
    yl = START + inc * np.arange(N_MONTH)
    yl_obs = yl * np.exp(rng.normal(0, NOISE, N_MONTH))
    lin3, lg3 = judge(yl)
    lin3o, lg3o = judge(yl_obs)
    straight = {"inc_per_month": inc, "rate_m1": round(inc / START, 4), "rate_m59": round(inc / yl[58], 4),
                "lin_ratio": round(lin3, 3), "log_ratio": round(lg3, 3),
                "lin_ratio_obs": round(lin3o, 3), "log_ratio_obs": round(lg3o, 3)}
    pd.DataFrame({"month": np.arange(N_MONTH), "true": yl, "members": np.round(yl_obs).astype(int)}) \
        .to_csv(DATA / "members_straight.csv", index=False)

    out = {"setting": {"months": N_MONTH, "change_month": CHANGE, "start": START, "noise_sd": NOISE,
                       "before": [int(BEFORE[0]), int(BEFORE[-1])], "after": [int(AFTER[0]), int(AFTER[-1])],
                       "after_early": [int(AFTER_EARLY[0]), int(AFTER_EARLY[-1])], "reps": N_REP},
           "example_4_to_3": ex, "summary": summ, "straight_line": straight}
    json.dump(out, open(RES / "a820_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：同じ数字を普通の軸と対数の軸で
    fig, axs = plt.subplots(1, 2, figsize=(8.6, 3.8))
    t = np.arange(N_MONTH)
    for ax, lgx, ttl, r in [(axs[0], False, "普通の軸", lin), (axs[1], True, "対数の軸", lg)]:
        ax.plot(t, y, color=BLUE, lw=1.6)
        for idx, c in [(BEFORE, GRAY), (AFTER, ORANGE)]:
            yy = y[idx]
            if lgx:
                b = slope(np.log(y), idx); fit = np.exp(np.log(yy).mean() + b * (idx - idx.mean()))
            else:
                b = slope(y, idx); fit = yy.mean() + b * (idx - idx.mean())
            ax.plot(idx, fit, color=c, lw=3, alpha=.8)
        ax.axvline(CHANGE, color=INK, lw=.6, ls=":")
        ax.text(CHANGE + 1, ax.get_ylim()[0] if not lgx else 1100, "伸び率 4%→3%", fontsize=8, va="bottom")
        if lgx:
            ax.set_yscale("log"); ax.set_yticks([1000, 2000, 4000, 8000]); ax.set_yticklabels(["1,000", "2,000", "4,000", "8,000"])
            ax.minorticks_off()
        else:
            ax.yaxis.set_major_formatter(COMMA)
        ax.set_xlabel("月"); ax.set_ylabel("会員数（人）")
        ax.set_title(f"{ttl}：後の傾き÷前の傾き＝{r:.2f}", fontsize=11)
    fig.suptitle("同じ数字でも、普通の軸では速まって見え、対数の軸では鈍って見える（灰：前の12か月、橙：最後の12か月）", fontsize=11)
    fig.tight_layout()
    save(fig, "a820_same_data.png", SRC)

    # 図2：伸び率 r1=4% のとき、r2 ごとに「鈍った」と読む割合
    g = grid[grid.r1 == 0.04]
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    ax.plot(g.r2 * 100, g.lin_slowed_share * 100, "o-", color=ORANGE, label="普通の軸で「鈍った」と読む")
    ax.plot(g.r2 * 100, g.log_slowed_share * 100, "o-", color=BLUE, label="対数の軸で「鈍った」と読む")
    ax.axvline(4, color=GRAY, lw=.8, ls="--"); ax.text(3.95, 72, "前と同じ4%", fontsize=8, ha="right", color=GRAY)
    ax.set_xlabel("36か月目からの伸び率 r2（%／月、前は4%）"); ax.set_ylabel("「鈍った」と読む割合（%、200回）")
    ax.set_ylim(-3, 103); ax.legend(frameon=False, fontsize=9, loc="lower left")
    ax.set_title("伸び率が4%から下がっても、普通の軸で「鈍った」と読めるのは半分の2%前後から", fontsize=11)
    save(fig, "a820_judge_share.png", SRC)

    # 図3：毎月40人ずつ増える会社
    fig, axs = plt.subplots(1, 2, figsize=(8.6, 3.6))
    for ax, lgx, ttl in [(axs[0], False, "普通の軸：まっすぐ"), (axs[1], True, "対数の軸：寝ていく")]:
        ax.plot(t, yl_obs, "o", color=GREEN, ms=2.5, alpha=.6, label="毎月の数（上下あり）")
        ax.plot(t, yl, color=GREEN, lw=1.6, label="置いた流れ")
        if lgx:
            ax.set_yscale("log"); ax.set_yticks([1000, 2000, 3000]); ax.set_yticklabels(["1,000", "2,000", "3,000"])
            ax.minorticks_off()
        else:
            ax.yaxis.set_major_formatter(COMMA)
        ax.set_xlabel("月"); ax.set_ylabel("会員数（人）"); ax.set_title(ttl, fontsize=11)
    fig.suptitle(f"毎月40人ずつ増える会社：伸び率は{inc/START*100:.1f}%から{inc/yl[58]*100:.1f}%に下がり続ける", fontsize=11)
    fig.tight_layout()
    save(fig, "a820_straight.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()

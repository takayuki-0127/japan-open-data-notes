"""892 単発の大きな案件1本で、平均の月収はどれだけ動くのか？（架空のデータ）

架空のフリーランス1人。ふだんの月の収入（続いている案件）は対数正規分布で上下する。
これに、まれに入る単発の大きな案件を足す。金額の単位は万円。数え方・読み方だけを扱う。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 892
SRC = "架空のフリーランスの月の収入（作成者が乱数で作成、seed 892）"
rng = np.random.default_rng(SEED)

ORD_MEDIAN, ORD_SD = 8.0, 0.25          # ふだんの月：中央値8万円・対数の標準偏差0.25
BIG_P, BIG_MEDIAN, BIG_SD = 1 / 24, 40.0, 0.5   # 単発の大きな案件：1か月あたりの確率・大きさ
EXAMPLE_BIG = 60.0                      # 例の1年：6月に60万円の案件
N_SIM = 20000


def ordinary(rng, shape, sd=ORD_SD, med=ORD_MEDIAN):
    return med * np.exp(rng.normal(0, sd, shape))


def big_jobs(rng, shape, p=BIG_P, med=BIG_MEDIAN, sd=BIG_SD):
    hit = rng.random(shape) < p
    return np.where(hit, med * np.exp(rng.normal(0, sd, shape)), 0.0)


def trim_max(x):
    """12か月のうちいちばん多い月を除いた平均"""
    return (x.sum(1) - x.max(1)) / (x.shape[1] - 1)


def forecast_eval(rng, p=BIG_P, big_med=BIG_MEDIAN, ord_sd=ORD_SD, n=N_SIM):
    """前の12か月から、次の12か月の月の平均を読む"""
    o1, o2 = ordinary(rng, (n, 12), ord_sd), ordinary(rng, (n, 12), ord_sd)
    b1, b2 = big_jobs(rng, (n, 12), p, big_med), big_jobs(rng, (n, 12), p, big_med)
    x1 = o1 + b1
    target_all = (o2 + b2).mean(1)          # 次の12か月の月の平均（単発込み）
    target_ord = o2.mean(1)                  # 次の12か月のふだんの月の平均（単発なし）
    pred = {"平均": x1.mean(1), "中央値": np.median(x1, 1), "いちばん多い月を除いた平均": trim_max(x1)}
    had = (b1 > 0).any(1)
    res = {"share_prev_year_with_big": round(float(had.mean()), 4),
           "share_next_year_with_big": round(float((b2 > 0).any(1).mean()), 4)}
    for k, v in pred.items():
        for tname, t in [("all", target_all), ("ord", target_ord)]:
            r = v / t
            res[f"{k}|{tname}|mape"] = round(float(np.mean(np.abs(r - 1))), 4)
            res[f"{k}|{tname}|over20"] = round(float((r >= 1.2).mean()), 4)
            res[f"{k}|{tname}|under20"] = round(float((r <= 1 / 1.2).mean()), 4)
            res[f"{k}|{tname}|bias_mean_ratio"] = round(float(v.mean() / t.mean()), 4)
            res[f"{k}|{tname}|over20_if_prev_big"] = round(float((r[had] >= 1.2).mean()), 4) if had.any() else None
    return res


def main():
    # 1) 例の2年：1年目の6月に60万円の単発、2年目は単発なし
    o = ordinary(rng, 24)
    big = np.zeros(24); big[5] = EXAMPLE_BIG
    ex = pd.DataFrame({"month_index": np.arange(1, 25), "year": np.repeat([1, 2], 12),
                       "month": np.tile(np.arange(1, 13), 2), "ordinary": o.round(4), "big_job": big,
                       "income": (o + big).round(4)})
    ex.to_csv(DATA / "example_2years.csv", index=False)
    ex = pd.read_csv(DATA / "example_2years.csv")
    y1, y2 = ex[ex.year == 1], ex[ex.year == 2]
    inc1, inc2 = y1.income.values, y2.income.values
    roll3 = ex.income.rolling(3).mean()
    roll12 = ex.income.rolling(12).mean()
    ord_med = float(np.median(y1.ordinary))
    example = {
        "year1_mean_without_big": round(float(y1.ordinary.mean()), 3),
        "year1_mean_with_big": round(float(inc1.mean()), 3),
        "year1_median_with_big": round(float(np.median(inc1)), 3),
        "year1_trim_max_mean": round(float(trim_max(inc1[None, :])[0]), 3),
        "big_share_of_year1_total": round(float(EXAMPLE_BIG / inc1.sum()), 4),
        "months_below_year1_mean": int((inc1 < inc1.mean()).sum()),
        "year2_mean": round(float(inc2.mean()), 3),
        "year2_vs_year1_mean_change": round(float(inc2.mean() / inc1.mean() - 1), 4),
        "year2_vs_year1_ordinary_change": round(float(inc2.mean() / y1.ordinary.mean() - 1), 4),
        "roll3_max": round(float(roll3.max()), 3),
        "roll3_months_ge_1_5x_ordinary_median": int((roll3 >= 1.5 * ord_med).sum()),
        "roll12_months_ge_1_2x_ordinary_median": int((roll12 >= 1.2 * ord_med).sum()),
        "june_vs_next_june_change": round(float(inc2[5] / inc1[5] - 1), 4),
        "year1_ordinary_median": round(ord_med, 3)}
    pd.DataFrame({"month_index": ex.month_index, "income": ex.income, "roll3": roll3.round(3),
                  "roll12": roll12.round(3)}).to_csv(RES / "example_rolling.csv", index=False)

    # 2) 式：大きさ S の案件1本で、W か月の平均がいくら上がるか（= S ÷ W）。ふだんの月の期待値に対する倍率
    e_ord = ORD_MEDIAN * np.exp(ORD_SD ** 2 / 2)
    tab = []
    for s in [10, 30, 60, 100]:
        for w in [1, 3, 6, 12]:
            tab.append({"big_job": s, "window_months": w, "rise_man": round(s / w, 3),
                        "ratio_to_ordinary": round((e_ord + s / w) / e_ord, 3)})
    tab = pd.DataFrame(tab)
    tab.to_csv(RES / "window_formula.csv", index=False)

    # 3) 前の12か月から次の12か月を読む（2万人年）
    base = forecast_eval(np.random.default_rng(SEED * 10))

    # 4) 置き方を変えると
    rob = []
    settings = [("基本（2年に1回・中央値40万円・ふだんの上下0.25）", BIG_P, BIG_MEDIAN, ORD_SD),
                ("単発なし", 0.0, BIG_MEDIAN, ORD_SD),
                ("4年に1回", 1 / 48, BIG_MEDIAN, ORD_SD),
                ("1年に1回", 1 / 12, BIG_MEDIAN, ORD_SD),
                ("半年に1回", 1 / 6, BIG_MEDIAN, ORD_SD),
                ("大きさ中央値20万円", BIG_P, 20.0, ORD_SD),
                ("大きさ中央値80万円", BIG_P, 80.0, ORD_SD),
                ("ふだんの上下0.10", BIG_P, BIG_MEDIAN, 0.10),
                ("ふだんの上下0.40", BIG_P, BIG_MEDIAN, 0.40)]
    for k, (name, p, bm, osd) in enumerate(settings):
        r = forecast_eval(np.random.default_rng(SEED * 1000 + k), p, bm, osd)
        rob.append({"setting": name, "p_per_month": round(p, 4), "big_median": bm, "ord_sd": osd, **r})
    rob = pd.DataFrame(rob)
    rob.to_csv(RES / "robustness.csv", index=False)

    def best(row, t):
        ks = ["平均", "中央値", "いちばん多い月を除いた平均"]
        return min(ks, key=lambda k: row[f"{k}|{t}|mape"])
    rob_best = {r["setting"]: {"best_for_all": best(r, "all"), "best_for_ord": best(r, "ord")}
                for _, r in rob.iterrows()}

    out = {"settings_base": {"ordinary_median": ORD_MEDIAN, "ordinary_sd_log": ORD_SD,
                             "ordinary_expected": round(float(e_ord), 3), "big_p_per_month": round(BIG_P, 4),
                             "big_median": BIG_MEDIAN, "big_sd_log": BIG_SD, "example_big": EXAMPLE_BIG,
                             "n_sim": N_SIM},
           "example": example, "forecast_base": base, "robustness_best": rob_best}
    json.dump(out, open(RES / "a892_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：例の2年
    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    ax.bar(ex.month_index, ex.ordinary, color=LIGHT, label="ふだんの案件")
    ax.bar(ex.month_index, ex.big_job, bottom=ex.ordinary, color=ORANGE, alpha=.8, label="単発の大きな案件（60万円）")
    ax.plot(ex.month_index, roll3, color=BLUE, lw=1.8, label="直近3か月の平均")
    ax.plot(ex.month_index, roll12, color=INK, lw=1.4, ls="--", label="直近12か月の平均")
    ax.set_ylim(0, 75)
    ax.set_xticks(range(1, 25, 2), [f"{(i - 1) % 12 + 1}月" if i <= 12 else f"翌{(i - 1) % 12 + 1}月"
                                    for i in range(1, 25, 2)], fontsize=8.5)
    ax.set_ylabel("月の収入（万円）")
    ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    ax.set_title("60万円の1本は、直近12か月の平均に12か月残り、抜けると「下がった」に見える", fontsize=11.5)
    save(fig, "a892_year.png", SRC)

    # 図2：式（大きさ × 何か月の平均か）
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    cols = {10: LIGHT, 30: BLUE, 60: ORANGE, 100: INK}
    for s, g in tab.groupby("big_job"):
        ax.plot(g.window_months, g.ratio_to_ordinary, marker="o", color=cols[s], label=f"単発{s}万円")
        last = g.iloc[-1]
        ax.text(12.3, last.ratio_to_ordinary, f"{last.ratio_to_ordinary:.2f}倍", va="center", fontsize=8.5,
                color=cols[s])
    ax.set_yscale("log"); ax.set_xticks([1, 3, 6, 12]); ax.set_xlim(0.5, 13.8)
    ax.set_yticks([1, 2, 5, 10]); ax.set_yticklabels(["1倍", "2倍", "5倍", "10倍"])
    ax.set_xlabel("何か月の平均で見るか"); ax.set_ylabel("ふだんの月に対する倍率（対数の目盛り）")
    ax.legend(frameon=False, fontsize=9)
    ax.set_title("平均の上がり方は「単発の額 ÷ 月数」の式で決まる（ふだんの月8.25万円）", fontsize=11.5)
    save(fig, "a892_window.png", SRC)

    # 図3：前の12か月から次の12か月の平均を読む：単発の頻度ごとの外れ（単発込みの次の12か月）
    sub = rob[rob.setting.isin([settings[i][0] for i in [1, 2, 0, 3, 4]])].set_index("setting").loc[
        [settings[i][0] for i in [1, 2, 0, 3, 4]]]
    labels = ["単発なし", "4年に1回", "2年に1回\n（基本）", "1年に1回", "半年に1回"]
    xs = np.arange(len(sub))
    fig, axes = plt.subplots(1, 2, figsize=(9.0, 4.2))
    preds = [("平均", ORANGE), ("中央値", BLUE), ("いちばん多い月を除いた平均", GRAY)]
    for j, (k, c) in enumerate(preds):
        vals = sub[f"{k}|all|mape"].values * 100
        axes[0].bar(xs + (j - 1) * 0.27, vals, width=0.27, color=c, label=f"前の12か月の{k}")
        for xx, vv in zip(xs + (j - 1) * 0.27, vals):
            axes[0].text(xx, vv + 0.5, f"{vv:.0f}", ha="center", fontsize=7)
        bias = (sub[f"{k}|all|bias_mean_ratio"].values - 1) * 100
        axes[1].bar(xs + (j - 1) * 0.27, bias, width=0.27, color=c)
        for xx, vv in zip(xs + (j - 1) * 0.27, bias):
            axes[1].text(xx, vv + (0.8 if vv >= 0 else -0.8), f"{int(round(vv)):+d}", ha="center",
                         va="bottom" if vv >= 0 else "top", fontsize=7)
    for a_ in axes:
        a_.set_xticks(xs, labels, fontsize=8)
        a_.set_xlabel("単発の大きな案件が入る頻度（平均して）", fontsize=9)
    axes[0].set_ylim(0, 52)
    axes[0].set_ylabel("1年ごとの外れの大きさの平均（%）", fontsize=9)
    axes[0].set_title("単発が入ると、1年ごとの外れは平均がいちばん大きい", fontsize=11)
    axes[0].legend(frameon=False, fontsize=7.5, loc="upper left")
    axes[1].axhline(0, color=INK, lw=.8); axes[1].set_ylim(-52, 12)
    axes[1].set_ylabel("2万組の合計で見た偏り（%）", fontsize=9)
    axes[1].set_title("長い目で合うのは平均（中央値は低く出る）", fontsize=11)
    fig.suptitle("前の12か月から、次の12か月の月の平均（単発込み）を読む", fontsize=12.5, y=1.02)
    fig.tight_layout()
    save(fig, "a892_forecast.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print(rob.filter(regex="setting|share|mape").to_string())
    print(rob.filter(regex="setting|over20$|bias").to_string())


if __name__ == "__main__":
    main()

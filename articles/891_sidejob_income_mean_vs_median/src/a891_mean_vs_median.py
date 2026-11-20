"""891 月の収入は、平均で見るか中央値で見るかで、どれだけ違って見えるのか？（架空のデータ）

架空の副業の人たち。人ごとの「ふだんの月の収入の水準」を対数正規分布で置き、
月ごとの上下（対数正規）と、案件のない月（0円）を確率で入れる。
金額の単位は万円。数え方・読み方だけを扱う。
"""
import json
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 891
SRC = "架空の副業の人の月の収入（作成者が乱数で作成、seed 891）"
rng = np.random.default_rng(SEED)

BASE = {"level_median": 3.0, "sd_person": 1.0, "sd_month": 0.5, "p_zero": 0.15}


def make_income(rng, n_people, n_month, sd_person=1.0, sd_month=0.5, p_zero=0.15, level_median=3.0):
    """人ごとの水準 × 月ごとの上下。p_zero の確率でその月は0円"""
    level = level_median * np.exp(rng.normal(0, sd_person, n_people))
    x = level[:, None] * np.exp(rng.normal(0, sd_month, (n_people, n_month)))
    zero = rng.random((n_people, n_month)) < p_zero
    x[zero] = 0.0
    return level, x


def phi(z):
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def summ(v):
    v = np.asarray(v)
    m, md = float(v.mean()), float(np.median(v))
    top = np.sort(v)[::-1][: max(1, len(v) // 10)]
    return {"mean": round(m, 3), "median": round(md, 3), "ratio_mean_median": round(m / md, 3) if md > 0 else None,
            "share_below_mean": round(float((v < m).mean()), 4),
            "top10_share_of_total": round(float(top.sum() / v.sum()), 4),
            "share_zero": round(float((v == 0).mean()), 4)}


def main():
    # 1) 1,000人×12か月（data に置く）
    level, x = make_income(rng, 1000, 12, **{k: BASE[k] for k in ["sd_person", "sd_month", "p_zero"]})
    rows = [{"person_id": i + 1, "month": m + 1, "income_man": round(float(x[i, m]), 4)}
            for i in range(1000) for m in range(12)]
    pd.DataFrame(rows).to_csv(DATA / "income_1000people_12months.csv", index=False)
    x = pd.read_csv(DATA / "income_1000people_12months.csv").pivot(index="person_id", columns="month",
                                                                      values="income_man").values

    m1 = x[:, 0]
    one_month = summ(m1)
    one_month_paid = summ(m1[m1 > 0])
    one_month_paid["n"] = int((m1 > 0).sum())
    yearly = x.mean(1)
    yearly_s = summ(yearly)
    # 月ごとの平均・中央値（12か月）
    by_month = pd.DataFrame({"month": np.arange(1, 13), "mean": x.mean(0).round(3),
                             "median": np.median(x, 0).round(3),
                             "share_below_mean": [(x[:, m] < x[:, m].mean()).mean().round(4) for m in range(12)]})
    by_month.to_csv(RES / "by_month.csv", index=False)

    # 1人の12か月：自分の12か月の平均を下回った月の割合
    pm = x.mean(1, keepdims=True)
    ok = pm[:, 0] > 0
    below_own = (x[ok] < pm[ok]).mean(1)
    own_med = np.median(x[ok], 1)
    own_ratio = pm[ok, 0] / np.where(own_med > 0, own_med, np.nan)
    person = {"share_months_below_own_mean": round(float(below_own.mean()), 4),
              "median_ratio_own_mean_to_own_median": round(float(np.nanmedian(own_ratio)), 3),
              "share_people_own_mean_ge_1_2x_own_median": round(float(np.nanmean(own_ratio >= 1.2)), 4)}

    # 2) 全体（20万人の1か月）と、少ない人数に聞いたときの振れ
    _, big = make_income(np.random.default_rng(SEED * 10), 200000, 1, BASE["sd_person"], BASE["sd_month"],
                         BASE["p_zero"])
    big = big[:, 0]
    pop = summ(big)
    samp = {}
    srng = np.random.default_rng(SEED * 100)
    sample_store = {}
    for n in [10, 20, 50, 200]:
        idx = srng.integers(0, len(big), (10000, n))
        s = big[idx]
        sm, sd = s.mean(1), np.median(s, 1)
        rm, rd = sm / pop["mean"], sd / pop["median"]
        samp[str(n)] = {"mean_p10_ratio": round(float(np.quantile(rm, .1)), 3),
                        "mean_p90_ratio": round(float(np.quantile(rm, .9)), 3),
                        "median_p10_ratio": round(float(np.quantile(rd, .1)), 3),
                        "median_p90_ratio": round(float(np.quantile(rd, .9)), 3),
                        "share_mean_off_30pct": round(float((np.abs(rm - 1) >= .3).mean()), 4),
                        "share_median_off_30pct": round(float((np.abs(rd - 1) >= .3).mean()), 4),
                        "share_sample_mean_ge_2x_pop_median": round(float((sm >= 2 * pop["median"]).mean()), 4),
                        "share_sample_mean_below_pop_mean": round(float((sm < pop["mean"]).mean()), 4)}
        if n == 20:
            sample_store = {"rm": rm, "rd": rd}
    pd.DataFrame(samp).T.rename_axis("n_people").to_csv(RES / "small_sample.csv")

    # 3) 置き方を変えると（各20万人の1か月）
    rob = []
    settings = [(sp, 0.5, pz) for sp in [0.6, 1.0, 1.4] for pz in [0.0, 0.15, 0.3]] + [(1.0, 0.3, 0.15),
                                                                                    (1.0, 0.8, 0.15)]
    for k, (sp, sm_, pz) in enumerate(settings):
        _, v = make_income(np.random.default_rng(SEED * 1000 + k), 200000, 1, sp, sm_, pz)
        r = summ(v[:, 0])
        s = math.sqrt(sp ** 2 + sm_ ** 2)
        rob.append({"sd_person": sp, "sd_month": sm_, "p_zero": pz, **r,
                    "formula_ratio_no_zero": round(math.exp(s ** 2 / 2), 3),
                    "formula_share_below_no_zero": round(phi(s / 2), 4)})
    rob = pd.DataFrame(rob)
    rob.to_csv(RES / "robustness.csv", index=False)

    out = {"settings_base": BASE, "one_month_1000": one_month, "one_month_1000_paid_only": one_month_paid,
           "yearly_avg_per_person_1000": yearly_s, "person_12months": person, "population_200000": pop,
           "small_sample_10000draws": samp,
           "robustness_range": {"ratio_min": float(rob.ratio_mean_median.min()),
                                "ratio_max": float(rob.ratio_mean_median.max()),
                                "below_min": float(rob.share_below_mean.min()),
                                "below_max": float(rob.share_below_mean.max())}}
    json.dump(out, open(RES / "a891_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：1,000人の1か月の収入
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    cap = 25
    v = np.where(m1 >= cap, cap + 0.25, m1)
    ax.hist(v[m1 > 0], bins=np.arange(0, cap + 1.0, 0.5), color=LIGHT)
    ax.axvline(one_month["median"], color=BLUE, lw=1.6)
    ax.axvline(one_month["mean"], color=ORANGE, lw=1.6, ls="--", ymax=0.86)
    yt = ax.get_ylim()[1]
    ax.text(one_month["median"] + 0.3, yt * .93, f"中央値 {one_month['median']:.2f}万円", color=BLUE, fontsize=9)
    ax.text(one_month["mean"] + 0.3, yt * .80, f"平均 {one_month['mean']:.2f}万円", color=ORANGE, fontsize=9)
    n_over = int((m1 >= cap).sum())
    ax.text(cap - 0.3, yt * .45, f"右端の棒は\n{cap}万円以上の{n_over}人", ha="right", fontsize=8.5, color=INK)
    ax.set_xlabel("その月の収入（万円）。0円の人（%d人）は棒に入れていない" % int((m1 == 0).sum()))
    ax.set_ylabel("人数")
    ax.set_title(f"平均を下回った人は{one_month['share_below_mean'] * 100:.1f}%（架空の1,000人の1か月）")
    save(fig, "a891_hist.png", SRC)

    # 図2：20人に聞いたときの平均・中央値の振れ
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    bins = np.linspace(0, 3.5, 71)
    ax.hist(np.minimum(sample_store["rm"], 3.49), bins=bins, color=ORANGE, alpha=.55, density=True,
            label="20人の平均 ÷ 全体の平均")
    ax.hist(np.minimum(sample_store["rd"], 3.49), bins=bins, color=BLUE, alpha=.55, density=True,
            label="20人の中央値 ÷ 全体の中央値")
    ax.axvline(1, color=INK, lw=1)
    ax.set_yticks([]); ax.set_xlabel("全体の値に対する比（1なら全体と同じ。3.5以上は右端に入れた）")
    ax.legend(frameon=False, fontsize=9)
    ax.set_title(f"20人に聞いた平均は、{samp['20']['share_sample_mean_below_pop_mean']*100:.0f}%の回で全体の平均を下回った（1万回）")
    save(fig, "a891_sample.png", SRC)

    # 図3：置き方を変えたときの「平均を下回る人」の割合
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    lab = [f"人の差{r.sd_person}・月の上下{r.sd_month}・0円の月{int(r.p_zero * 100)}%" for r in rob.itertuples()]
    isbase = [(r.sd_person, r.sd_month, r.p_zero) == (1.0, 0.5, 0.15) for r in rob.itertuples()]
    ax.barh(lab[::-1], rob.share_below_mean[::-1] * 100, color=[BLUE if b else LIGHT for b in isbase[::-1]])
    for i, (val, rt) in enumerate(zip(rob.share_below_mean[::-1] * 100, rob.ratio_mean_median[::-1])):
        ax.text(val + 0.6, i, f"{val:.1f}%（平均は中央値の{rt:.2f}倍）", va="center", fontsize=8)
    ax.set_xlim(50, 100); ax.set_xlabel("その月の平均を下回った人の割合（%、各20万人）")
    ax.tick_params(axis="y", labelsize=8.5)
    ax.set_title("散らばりを大きく置くほど、平均を下回る人が増える（濃い棒が基本）")
    save(fig, "a891_settings.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print(rob.to_string())


if __name__ == "__main__":
    main()

"""875 「混んでいる」と感じる人の割合は、実際の混み具合と合うのか？（架空のデータ）

架空の店（売り場）。1日600分（10時〜20時）開き、平日と週末で客の数が違う。客は昼と夕方に多く来て、
店にいる時間は平均30分。店にいる人数÷目安の人数（100人）を「混み具合」とする。
客は、自分が店にいた間の混み具合（自分以外）の平均が、その人の感じ方の線を超えたら「混んでいる」と答えると置く。
店が時間で数える混み具合（時間で平均）と、客に聞いた「混んでいる」の割合（客の人数で平均）を比べる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from math import erf
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 875
SRC = "架空の店の混み具合と客の答え（作成者が乱数で作成、seed 875）"
T_OPEN, LAST_IN = 600, 570          # 営業600分、最後の入店は閉店30分前
CAP = 100                           # 目安の人数
N_DAYS = 350                        # 50週
WEEKDAY_N, WEEKEND_N = 1500, 2100   # 1日の客の数の平均（平日・週末）
DAY_SD = 0.12                       # 日ごとの客の数の揺れ（平均に対する割合）
STAY_MEAN, STAY_SD = 30.0, 15.0
TAU_MEAN, TAU_SD = 0.9, 0.15        # 「混んでいる」と感じる線（混み具合）の人ごとの散らばり
GRID = np.arange(0, T_OPEN + 1, 0.5)
phi = np.vectorize(lambda z: 0.5 * (1 + erf(z / np.sqrt(2))))


def profile(kind):
    t = GRID[GRID <= LAST_IN]
    if kind == "flat":
        p = np.ones_like(t)
    else:
        a = {"peak": 1.0, "peak_strong": 2.5}[kind]
        p = 1 + a * (1.0 * np.exp(-((t - 180) / 50) ** 2) + 0.8 * np.exp(-((t - 480) / 60) ** 2))
    cdf = np.cumsum(p); cdf = cdf / cdf[-1]
    return t, cdf


def simulate(rng, kind="peak", tau_mean=TAU_MEAN, keep_day=None):
    t, cdf = profile(kind)
    s2 = np.log(1 + (STAY_SD / STAY_MEAN) ** 2)
    rows, days = [], []
    keep = None
    for d in range(N_DAYS):
        weekend = d % 7 >= 5
        mu = (WEEKEND_N if weekend else WEEKDAY_N) * np.exp(rng.normal(0, DAY_SD))
        n = rng.poisson(mu)
        arr = np.sort(np.interp(rng.random(n), cdf, t))
        stay = rng.lognormal(np.log(STAY_MEAN) - s2 / 2, np.sqrt(s2), n)
        lev = arr + stay
        # 0.5分ごとの店にいる人数
        occ = np.searchsorted(arr, GRID, side="right") - np.searchsorted(np.sort(lev), GRID, side="right")
        r = occ / CAP
        cum = np.concatenate([[0], np.cumsum((r[1:] + r[:-1]) / 2 * 0.5)])
        lev_c = np.minimum(lev, T_OPEN)
        # 自分がいた間の混み具合の平均（自分の1人分を引く）
        exp_r = (np.interp(lev_c, GRID, cum) - np.interp(arr, GRID, cum)) / np.maximum(lev_c - arr, 1e-9) - 1 / CAP
        tau = rng.normal(tau_mean, TAU_SD, n)
        felt = exp_r > tau
        open_r = r[GRID < T_OPEN]
        days.append({"day": d, "weekend": int(weekend), "customers": n, "time_mean_ratio": open_r.mean(),
                     "time_share_over_line": (open_r > tau_mean).mean(),
                     "time_weighted_felt": phi((open_r - tau_mean) / TAU_SD).mean(),
                     "cust_mean_ratio": exp_r.mean(), "cust_share_over_line": (exp_r > tau_mean).mean(),
                     "felt_share": felt.mean(), "peak_ratio": open_r.max()})
        if keep_day is not None and d == keep_day:
            keep = (pd.DataFrame({"time_min": GRID, "people": occ}),
                    pd.DataFrame({"arrival": arr, "stay": stay, "experienced_ratio": exp_r, "threshold": tau,
                                  "felt_crowded": felt.astype(int)}))
    return pd.DataFrame(days), keep


def overall(dd):
    w = dd.customers
    return {"time_mean_ratio": round(float(dd.time_mean_ratio.mean()), 3),
            "time_share_over_line": round(float(dd.time_share_over_line.mean()), 3),
            "time_weighted_felt": round(float(dd.time_weighted_felt.mean()), 3),
            "cust_mean_ratio": round(float(np.average(dd.cust_mean_ratio, weights=w)), 3),
            "cust_share_over_line": round(float(np.average(dd.cust_share_over_line, weights=w)), 3),
            "felt_share": round(float(np.average(dd.felt_share, weights=w)), 3)}


def main():
    rng = np.random.default_rng(SEED)
    base, keep = simulate(rng, "peak", keep_day=5)       # 6日目＝週末の1日
    base.round(4).to_csv(DATA / "days_base.csv", index=False)
    keep[0].to_csv(DATA / "one_day_people.csv", index=False)
    keep[1].round(4).to_csv(DATA / "one_day_customers.csv", index=False)

    res = {"base": overall(base)}
    # 平日・週末
    res["base_weekday"] = overall(base[base.weekend == 0]); res["base_weekend"] = overall(base[base.weekend == 1])
    res["weekend_share_of_customers"] = round(float(base[base.weekend == 1].customers.sum() / base.customers.sum()), 3)
    res["weekend_share_of_days"] = round(float(base.weekend.mean()), 3)

    # 確かめ：山の強さ×感じ方の線
    sens = []
    for kind, lab in [("flat", "山なし"), ("peak", "昼と夕方に山（基本）"), ("peak_strong", "強い山")]:
        for tm in [0.7, 0.9, 1.1]:
            dd = base if (kind == "peak" and tm == TAU_MEAN) else simulate(rng, kind, tm)[0]
            o = overall(dd); o.update({"profile": kind, "label": lab, "tau_mean": tm,
                                       "felt_minus_time_weighted": round(o["felt_share"] - o["time_weighted_felt"], 3),
                                       "felt_over_time_weighted": round(o["felt_share"] / max(o["time_weighted_felt"], 1e-9), 2)})
            sens.append(o)
    sens = pd.DataFrame(sens)
    sens.to_csv(RES / "sensitivity.csv", index=False)

    # 日ごと：店の1日平均の混み具合と、「混んでいる」と答えた割合
    base["bin"] = pd.cut(base.time_mean_ratio, [0, .5, .6, .7, .8, .9, 1.0, 2])
    bins = base.groupby("bin", observed=True).agg(days=("day", "size"), time_mean=("time_mean_ratio", "mean"),
                                                  felt=("felt_share", "mean"), felt_min=("felt_share", "min"),
                                                  felt_max=("felt_share", "max")).round(3)
    bins.index = bins.index.astype(str)
    bins.to_csv(RES / "by_day_level.csv")
    res["day_corr_time_mean_vs_felt"] = round(float(np.corrcoef(base.time_mean_ratio, base.felt_share)[0, 1]), 3)
    res["day_corr_rank"] = round(float(base[["time_mean_ratio", "felt_share"]].rank().corr().iloc[0, 1]), 3)
    # 山の強さで比べる：1日の平均の混み具合がほぼ同じ日（0.75〜0.85）どうし
    pairs, prof_days = {}, {}
    for kind in ["flat", "peak", "peak_strong"]:
        dd = base if kind == "peak" else simulate(np.random.default_rng(SEED * 10 + len(kind)), kind)[0]
        prof_days[kind] = dd
        res.setdefault("day_corr_rank_by_profile", {})[kind] = round(float(dd[["time_mean_ratio", "felt_share"]].rank().corr().iloc[0, 1]), 3)
        pairs[kind] = {}
        for lo, hi in [(0.65, 0.75), (0.75, 0.85), (1.05, 1.15)]:
            m = dd[dd.time_mean_ratio.between(lo, hi)]
            pairs[kind][f"{lo:.2f}-{hi:.2f}"] = {"days": int(len(m)), "time_mean_ratio": round(float(m.time_mean_ratio.mean()), 3),
                                                 "felt_share": round(float(np.average(m.felt_share, weights=m.customers)), 3)}
    res["same_level_days_by_profile"] = pairs
    res["sensitivity"] = sens.to_dict("records")
    res["one_day"] = {"day": 5, "customers": int(len(keep[1])), "peak_people": int(keep[0].people.max()),
                      "time_mean_ratio": round(float(keep[0].people[keep[0].time_min < T_OPEN].mean() / CAP), 3),
                      "felt_share": round(float(keep[1].felt_crowded.mean()), 3)}
    json.dump(res, open(RES / "a875_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：ある1日の人数と来た客の数
    p, c = keep
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    ax.plot(p.time_min / 60 + 10, p.people / CAP * 100, color=BLUE, lw=1.4, label="店にいる人数（目安の人数に対する%）")
    ax.axhline(TAU_MEAN * 100, color=ORANGE, lw=1, ls="--", label="「混んでいる」と感じる線（人ごとの平均）")
    ax2 = ax.twinx(); ax2.spines["right"].set_visible(True)
    h = np.histogram(c.arrival, bins=np.arange(0, 601, 30))[0]
    ax2.bar(np.arange(0, 600, 30) / 60 + 10.25, h, width=.45, color=GRAY, alpha=.35)
    ax2.set_ylabel("30分ごとに来た客（人、灰色の棒）", color=GRAY)
    ax.set_xlabel("時刻（時）"); ax.set_ylabel("混み具合（%）")
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    ax.set_title(f"混む時間ほど客が多い。客は「混んだ時間」を多めに体験する（ある週末の1日）")
    save(fig, "a875_one_day.png", SRC)

    # 図2：時間で数えた値と客で数えた値
    b = res["base"]
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    labs = ["混み具合の平均（%）", "「混んでいる」の割合（%）"]
    x = np.arange(2)
    ax.bar(x - 0.18, [b["time_mean_ratio"] * 100, b["time_weighted_felt"] * 100], 0.36, color=GRAY,
           label="時間で数える（営業中のどの時刻も同じ重み）")
    ax.bar(x + 0.18, [b["cust_mean_ratio"] * 100, b["felt_share"] * 100], 0.36, color=BLUE,
           label="客に聞く（来た客1人ずつ同じ重み）")
    for xi, (u, v) in enumerate([(b["time_mean_ratio"], b["cust_mean_ratio"]), (b["time_weighted_felt"], b["felt_share"])]):
        ax.text(xi - 0.18, u * 100 + 1.5, f"{u*100:.0f}", ha="center", fontsize=9.5)
        ax.text(xi + 0.18, v * 100 + 1.5, f"{v*100:.0f}", ha="center", fontsize=9.5)
    ax.set_xticks(x); ax.set_xticklabels(labs); ax.set_ylim(0, max(b["cust_mean_ratio"], b["felt_share"]) * 125)
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    ax.set_title("同じ店・同じ日々でも、客に聞くと時間で数えるより混んで見える（350日）")
    save(fig, "a875_weight.png", SRC)

    # 図3：日ごとの散布図
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    for kind, colr, lab in [("flat", GREEN, "山なし"), ("peak", BLUE, "昼と夕方に山（基本）"), ("peak_strong", ORANGE, "強い山")]:
        d = prof_days[kind]
        ax.scatter(d.time_mean_ratio * 100, d.felt_share * 100, s=10, color=colr, alpha=.55, lw=0, label=lab)
    ax.set_xlabel("その日の混み具合の平均（店が時間で数える、%）"); ax.set_ylabel("「混んでいる」と答えた客の割合（%）")
    ax.legend(frameon=False, fontsize=9, title="客の来方（1点が1日）", title_fontsize=9); ax.set_ylim(0, 100)
    ax.set_title(f"同じ店なら日ごとの順番はよく合う（順位相関{res['day_corr_rank']:.2f}）。\n山の形が違う店どうしでは、同じ混み具合でも答えの割合がずれる", fontsize=12)
    save(fig, "a875_days.png", SRC)
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()

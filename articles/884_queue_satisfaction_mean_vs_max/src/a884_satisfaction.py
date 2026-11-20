"""884 満足度は、待ち時間の平均と最長のどちらで決まるのか？（架空のデータ）

架空のテイクアウトの店（窓口3つ、1列に並ぶ）。1日10時間、2,000日。
日ごとに客の多さ（1時間55〜85人）と昼の山の高さ（0〜0.6倍増し、11:30〜13:00ごろ）を変える。
1人の受け渡しは平均2分（指数分布）。
客1人ずつの満足（10点満点）は、その人の待ちだけで決まると作成者が置く（決まり方は5通り）。
日ごとの待ちの指標（平均・最長・上位10%の線・10分以上待った人の割合）が、
その日の満足（全員の平均と、40人に聞いたアンケートの平均）とどれだけ合うかを数える。
"""
import json, time
from heapq import heapreplace
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 884
SRC = "架空のテイクアウトの店（作成者が乱数で作成、seed 884）"
DAY, C, SVC = 600.0, 3, 2.0
N_DAYS, N_SURVEY = 2000, 40

# 1人の満足の決まり方（待ち w 分）：基準8点 − 1分あたり a 点 − （w が線以上なら）b 点
RULES = {
    "基本：1分0.1点＋10分以上で2点": (0.10, 2.0, 10.0),
    "毎分だけ：1分0.25点": (0.25, 0.0, 10.0),
    "線だけ：10分以上で3点": (0.0, 3.0, 10.0),
    "線を5分に：1分0.1点＋5分以上で2点": (0.10, 2.0, 5.0),
    "線を15分に：1分0.1点＋15分以上で2点": (0.10, 2.0, 15.0),
}
METRICS = {"mean": "平均の待ち", "max": "最長の待ち", "p90": "上位10%の待ち（90%の線）",
           "share10": "10分以上待った人の割合"}


def make_day(rng):
    per_hour = rng.uniform(55, 85)
    peak = rng.uniform(0, 0.6)
    # 来る勢い：基本 × (1 + peak × 昼の山)。山は 210分目（11:30相当）〜300分目に置く形
    lam_max = per_hour / 60 * (1 + peak)
    n = rng.poisson(lam_max * DAY)
    t = np.sort(rng.uniform(0, DAY, n))
    bump = np.exp(-0.5 * ((t - 255) / 30) ** 2)
    keep = rng.uniform(size=n) < (1 + peak * bump) / (1 + peak)
    arr = t[keep]
    s = rng.exponential(SVC, len(arr))
    return per_hour, peak, arr, s


def waits(arr, s, c=C):
    free = [0.0] * c
    w = np.empty(len(arr))
    for i, (a, d) in enumerate(zip(arr.tolist(), s.tolist())):
        f = free[0]
        st = a if a > f else f
        w[i] = st - a
        heapreplace(free, st + d)
    return w


def person_sat(w, rule, noise=None):
    a, b, line = rule
    s = 8.0 - a * w - b * (w >= line)
    if noise is not None:
        s = np.clip(s + noise, 0, 10)
    return s


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    days, wlist = [], []
    for d in range(N_DAYS):
        ph, pk, arr, s = make_day(rng)
        w = waits(arr, s)
        wlist.append(w)
        days.append({"day": d + 1, "per_hour": ph, "peak": pk, "n": len(w), "mean": w.mean(), "max": w.max(),
                     "p90": np.quantile(w, .9), "share10": (w >= 10).mean()})
    days = pd.DataFrame(days)

    # 満足：全員の平均（ゆれなし）と、40人に聞いたアンケートの平均（1人ごとのゆれ 標準偏差1.5、0〜10で切る）
    sat_rows = []
    for rname, rule in RULES.items():
        r2 = np.random.default_rng(SEED + 7)   # どの決まり方でも同じ回答者・同じゆれ
        for d, w in enumerate(wlist):
            true = person_sat(w, rule).mean()
            idx = r2.choice(len(w), N_SURVEY, replace=False)
            noise = r2.normal(0, 1.5, N_SURVEY)
            surv = person_sat(w[idx], rule, noise).mean()
            idx10 = idx[:10]
            surv10 = person_sat(w[idx10], rule, noise[:10]).mean()
            sat_rows.append({"rule": rname, "day": d + 1, "sat_all": true, "sat_survey40": surv,
                             "sat_survey10": surv10})
    sat = pd.DataFrame(sat_rows)

    base_rule = list(RULES)[0]
    one = days.merge(sat[sat.rule == base_rule].drop(columns="rule"), on="day")
    one.to_csv(DATA / "days.csv", index=False, float_format="%.4f")

    # 相関（2,000日）と、200日ずつの組100組で「いちばん合った指標」の回数
    corr_rows, win_rows = [], []
    sub_rng = np.random.default_rng(SEED + 11)
    subsets = [sub_rng.choice(N_DAYS, 200, replace=False) for _ in range(100)]
    for rname in RULES:
        m = days.merge(sat[sat.rule == rname], on="day")
        for target in ["sat_all", "sat_survey40", "sat_survey10"]:
            row = {"rule": rname, "target": target}
            for k in METRICS:
                row[k] = round(float(np.corrcoef(m[k], m[target])[0, 1]), 3)
            corr_rows.append(row)
            wins = {k: 0 for k in METRICS}
            for sub in subsets:
                mm = m.iloc[sub]
                rs = {k: abs(np.corrcoef(mm[k], mm[target])[0, 1]) for k in METRICS}
                wins[max(rs, key=rs.get)] += 1
            win_rows.append({"rule": rname, "target": target, **wins})
    corr = pd.DataFrame(corr_rows); win = pd.DataFrame(win_rows)
    corr.to_csv(RES / "correlations.csv", index=False)
    win.to_csv(RES / "best_metric_wins_200days.csv", index=False)

    # 指標どうしの相関（日ごと）と、最長と客数・昼の山の関係
    mcorr = days[["mean", "max", "p90", "share10", "n", "peak"]].corr().round(3)
    mcorr.to_csv(RES / "metric_correlations.csv")

    # 平均が同じくらいの日（平均の待ち 1.5〜2.5分）で、最長の幅と満足の幅
    band = one[(one["mean"] >= 1.5) & (one["mean"] <= 2.5)]
    lo, hi = band["max"].quantile(.1), band["max"].quantile(.9)
    band_info = {"days": int(len(band)), "max_p10": round(float(lo), 2), "max_p90": round(float(hi), 2),
                 "sat_all_when_max_low": round(float(band[band["max"] <= lo].sat_all.mean()), 3),
                 "sat_all_when_max_high": round(float(band[band["max"] >= hi].sat_all.mean()), 3),
                 "share10_when_max_low": round(float(band[band["max"] <= lo].share10.mean()), 4),
                 "share10_when_max_high": round(float(band[band["max"] >= hi].share10.mean()), 4)}

    # 平均が同じくらいの日の中で、各指標と満足（全員）の相関（決まり方ごと）
    band_days = set(band.day)
    inband = []
    for rname in RULES:
        m = days.merge(sat[sat.rule == rname], on="day")
        m = m[m.day.isin(band_days)]
        inband.append({"rule": rname, **{k: round(float(np.corrcoef(m[k], m.sat_all)[0, 1]), 3) for k in METRICS}})
    inband = pd.DataFrame(inband)
    inband.to_csv(RES / "correlations_same_mean_band.csv", index=False)

    # 決まり方ごとの順位（全員の満足との相関の大きさ）
    ranks = {}
    for r in corr[corr.target == "sat_all"].itertuples():
        v = {k: abs(getattr(r, k)) for k in METRICS}
        order = sorted(v, key=v.get, reverse=True)
        ranks[r.rule] = {"best": order[0], "worst": order[-1], "best_minus_max": round(v[order[0]] - v["max"], 3)}

    desc = days[["n", "mean", "max", "p90", "share10"]].describe(percentiles=[.1, .5, .9]).round(3)
    out = {"setting": {"days": N_DAYS, "windows": C, "service_mean_min": SVC, "survey_n": N_SURVEY,
                       "rules": {k: {"per_min": v[0], "drop": v[1], "line_min": v[2]} for k, v in RULES.items()}},
           "day_metrics_summary": desc.to_dict(),
           "correlations": corr.to_dict("records"), "wins_200days_x100": win.to_dict("records"),
           "metric_correlations": mcorr.to_dict(), "same_mean_band": band_info,
           "same_mean_band_correlations": inband.to_dict("records"), "ranks_sat_all": ranks}
    json.dump(out, open(RES / "a884_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：平均の待ち・最長の待ちと、アンケートの満足（基本の決まり方）
    fig, axs = plt.subplots(1, 2, figsize=(8.4, 3.8), sharey=True)
    cb = corr[(corr.rule == base_rule) & (corr.target == "sat_survey40")].iloc[0]
    for ax, k, cl in [(axs[0], "mean", BLUE), (axs[1], "max", ORANGE)]:
        ax.scatter(one[k], one.sat_survey40, s=5, color=cl, alpha=.35, lw=0)
        ax.set_xlabel(f"その日の{METRICS[k]}（分）")
        ax.set_title(f"{METRICS[k]}：相関 {cb[k]:.2f}", fontsize=11.5)
    axs[0].set_ylabel("その日のアンケートの満足（40人の平均、10点満点）")
    fig.suptitle("基本の決まり方で：満足は平均の待ちとよく並び、最長とはばらける", fontsize=12.5, y=1.02)
    save(fig, "a884_scatter.png", SRC)

    # 図2：決まり方ごとの相関（全員の満足）
    ca = corr[corr.target == "sat_all"].reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    wdt = 0.2; cols = [BLUE, ORANGE, GRAY, GREEN]
    ylab = [r.split("：")[0] + "\n" + r.split("：")[1] for r in ca.rule]
    for j, (k, cl) in enumerate(zip(METRICS, cols)):
        ax.barh(np.arange(len(ca)) + (j - 1.5) * wdt, ca[k].abs(), height=wdt, color=cl, label=METRICS[k])
    ax.set_yticks(np.arange(len(ca))); ax.set_yticklabels(ylab, fontsize=8.5); ax.invert_yaxis()
    ax.set_xlim(0, 1.05); ax.set_xlabel("その日の満足（全員の平均）との相関の大きさ（2,000日）")
    ax.legend(frameon=False, fontsize=8.5, loc="lower left", bbox_to_anchor=(0, -0.3), ncol=2)
    n_worst = sum(v["worst"] == "max" for v in ranks.values())
    ax.set_title(f"いちばん合う指標は置いた決まり方で入れ替わり、最長は{len(ranks)}通り中{n_worst}通りで最下位", fontsize=11.5)
    save(fig, "a884_rules.png", SRC, y=-0.13)

    # 図3：平均が同じくらいの日の中での相関（決まり方ごと）
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    for j, (k, cl) in enumerate(zip(METRICS, cols)):
        ax.barh(np.arange(len(inband)) + (j - 1.5) * wdt, inband[k].abs(), height=wdt, color=cl, label=METRICS[k])
    ax.set_yticks(np.arange(len(inband))); ax.set_yticklabels(ylab, fontsize=8.5); ax.invert_yaxis()
    ax.set_xlim(0, 1.05)
    ax.set_xlabel(f"その日の満足（全員の平均）との相関の大きさ（平均の待ち1.5〜2.5分の{len(band)}日）")
    ax.legend(frameon=False, fontsize=8.5, loc="lower left", bbox_to_anchor=(0, -0.3), ncol=2)
    ax.set_title("平均が同じくらいの日どうしでは、置いた決まり方の違いがはっきり出る", fontsize=11.5)
    save(fig, "a884_same_mean.png", SRC, y=-0.13)

    print(json.dumps(out, ensure_ascii=False, indent=1)[:200])
    print(corr.to_string()); print(win.to_string()); print(mcorr.to_string()); print(band_info); print(inband.to_string()); print(ranks); print(desc.to_string())
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()

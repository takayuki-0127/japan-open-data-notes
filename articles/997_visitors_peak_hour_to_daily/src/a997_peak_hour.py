"""997 ピークの1時間の人数から、1日の人数を見込むと？（架空のデータ）

架空の屋内の催事館「B館」（10時〜20時、10時間）。日の種類は平日・土日・催しの日（14時台にショー）の3つ。
1日の来場者の、時間ごとの割合の形（作成者が置く）と、1日の人数・時間ごとの振れから、
時間ごとの入館者数を作る。「ピークの1時間の人数×係数」で1日の人数を見込み、本当の1日の人数と比べる。
係数は、全部の時間を数えた日（較正の日）の「1日の人数÷ピークの1時間の人数」の平均。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 997
SRC = "架空の催事館の入館者（作成者が乱数で作成、seed 997）"
HOURS = np.arange(10, 20)
TYPES = ["平日", "土日", "催しの日"]
MEAN_DAY = {"平日": 3000.0, "土日": 6000.0, "催しの日": 8000.0}
DAY_SD = 0.2        # 1日の人数の振れ（対数の標準偏差）
HOUR_SD = 0.1       # 時間ごとの振れ（対数の標準偏差）
SPIKE = 0.15        # 催しの日に、14時台のショーに集まる割合
FIXED_HOUR = 13     # 決まった時間に数えるときの時間（13時台）
N_CAL = 10          # 係数を決めるのに全部の時間を数えた日の数
N_EVAL = 300        # 見込みを確かめる日の数（日の種類ごと）
REPS = 200


def profiles(spike=SPIKE):
    h = HOURS + 0.5
    wd = 1 + 0.5 * np.exp(-(h - 12.5) ** 2 / 2) + 0.45 * np.exp(-(h - 17.5) ** 2 / 1.5)
    we = 1 + 1.3 * np.exp(-(h - 14) ** 2 / (2 * 1.6 ** 2))
    wd, we = wd / wd.sum(), we / we.sum()
    ev = we * (1 - spike)
    ev[list(HOURS).index(14)] += spike
    return {"平日": wd, "土日": we, "催しの日": ev}


def days(rng, typ, n, prof, hour_sd=HOUR_SD, scale=1.0):
    T = MEAN_DAY[typ] * scale * np.exp(rng.normal(0, DAY_SD, n))
    lam = T[:, None] * prof[typ][None, :] * np.exp(rng.normal(0, hour_sd, (n, len(HOURS))))
    return rng.poisson(lam)


def k_of(c, kind):
    tot = c.sum(1)
    if kind == "peak":
        return float(np.mean(tot / c.max(1)))
    return float(np.mean(tot / c[:, list(HOURS).index(FIXED_HOUR)]))


def one_rep(rng, spike=SPIKE, hour_sd=HOUR_SD, scale=1.0, n_cal=N_CAL):
    prof = profiles(spike)
    cal = {t: days(rng, t, n_cal, prof, hour_sd, scale) for t in TYPES}
    kA = k_of(cal["平日"], "peak")
    kC = k_of(cal["平日"], "fixed")
    rows = []
    for t in TYPES:
        c = days(rng, t, N_EVAL, prof, hour_sd, scale)
        tot = c.sum(1)
        pk = c.max(1)
        fx = c[:, list(HOURS).index(FIXED_HOUR)]
        kB = k_of(cal[t], "peak")
        est = {"A": pk * kA, "B": pk * kB, "C": fx * kC}
        for m, e in est.items():
            err = (e / tot - 1) * 100
            rows.append({"type": t, "method": m, "mean_err_pct": err.mean(), "p10_err_pct": np.quantile(err, 0.1),
                         "p90_err_pct": np.quantile(err, 0.9), "within10_pct": (np.abs(err) <= 10).mean() * 100})
        prof_peak = int(np.argmax(prof[t]))
        rows.append({"type": t, "method": "info", "peak_share_obs_pct": float(np.mean(pk / tot) * 100),
                     "peak_share_profile_pct": float(prof[t].max() * 100),
                     "peak_hour_moved_pct": float(np.mean(c.argmax(1) != prof_peak) * 100),
                     "kA": kA, "kB": kB, "kC": kC})
    return pd.DataFrame(rows)


def summarize(sims):
    s = pd.concat(sims)
    m = s[s.method != "info"].groupby(["type", "method"])[["mean_err_pct", "p10_err_pct", "p90_err_pct", "within10_pct"]].mean()
    info = s[s.method == "info"].groupby("type")[["peak_share_obs_pct", "peak_share_profile_pct", "peak_hour_moved_pct",
                                                    "kA", "kB", "kC"]].mean()
    return m, info


def main():
    rng = np.random.default_rng(SEED)
    prof = profiles()
    # 形だけから出る値（振れがないとき）：係数＝1÷ピークの割合、見込みの比＝平日のピークの割合÷その日の種類のピークの割合
    form = {}
    for t in TYPES:
        form[t] = {"peak_share_pct": round(float(prof[t].max() * 100), 2),
                   "fixed13_share_pct": round(float(prof[t][list(HOURS).index(FIXED_HOUR)] * 100), 2),
                   "peak_hour": int(HOURS[np.argmax(prof[t])]),
                   "k_formula": round(float(1 / prof[t].max()), 3),
                   "A_err_formula_pct": round(float((prof[t].max() / prof["平日"].max() - 1) * 100), 1),
                   "C_err_formula_pct": round(float((prof[t][3] / prof["平日"][3] - 1) * 100), 1)}
    pd.DataFrame({"hour": HOURS, **{t: np.round(prof[t] * 100, 3) for t in TYPES}}).to_csv(RES / "profiles_pct.csv", index=False)

    sims = [one_rep(rng) for _ in range(REPS)]
    m, info = summarize(sims)
    m.round(2).to_csv(RES / "base_by_type_method.csv")
    info.round(3).to_csv(RES / "base_peak_info.csv")

    # 例の日：各種類10日分の時間ごとの入館者
    g = np.random.default_rng(SEED * 10)
    ex = []
    for t in TYPES:
        c = days(g, t, 10, prof)
        for i, row in enumerate(c):
            for h, v in zip(HOURS, row):
                ex.append({"type": t, "day": i + 1, "hour": int(h), "visitors": int(v)})
    ex = pd.DataFrame(ex)
    ex.to_csv(DATA / "hourly_example.csv", index=False)

    # 確かめ1：ショーの集まり方 × 時間ごとの振れ × 館の大きさ（18通り、各50回）
    grid = []
    for sp in [0.05, 0.15, 0.30]:
        for hs in [0.05, 0.1, 0.2]:
            for sc in [0.1, 1.0]:
                gg = np.random.default_rng(SEED * 1000 + int(sp * 100) * 10 + int(hs * 100) + int(sc * 10) * 1000)
                mm, ii = summarize([one_rep(gg, sp, hs, sc) for _ in range(50)])
                row = {"spike": sp, "hour_sd": hs, "scale": sc}
                for t in TYPES:
                    for meth in ["A", "B", "C"]:
                        row[f"{t}_{meth}_mean_err_pct"] = round(float(mm.loc[(t, meth), "mean_err_pct"]), 2)
                        row[f"{t}_{meth}_within10_pct"] = round(float(mm.loc[(t, meth), "within10_pct"]), 2)
                    row[f"{t}_peak_moved_pct"] = round(float(ii.loc[t, "peak_hour_moved_pct"]), 2)
                grid.append(row)
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid_spike_hoursd_scale.csv", index=False)
    # 確かめ2：係数を決める日の数（3・10・30日、各100回）
    cal = []
    for nc in [3, 10, 30]:
        gg = np.random.default_rng(SEED * 77 + nc)
        mm, _ = summarize([one_rep(gg, n_cal=nc) for _ in range(100)])
        for t in TYPES:
            cal.append({"n_cal": nc, "type": t, **{f"B_{k}": round(float(mm.loc[(t, "B"), k]), 2) for k in mm.columns},
                        "A_mean_err_pct": round(float(mm.loc[(t, "A"), "mean_err_pct"]), 2)})
    cal = pd.DataFrame(cal)
    cal.to_csv(RES / "by_n_calibration.csv", index=False)

    def rng_of(col):
        return [float(grid[col].min()), float(grid[col].max())]
    out = {"setting": {"hours": [int(HOURS[0]), int(HOURS[-1]) + 1], "mean_day": MEAN_DAY, "day_sd": DAY_SD, "hour_sd": HOUR_SD,
                       "spike": SPIKE, "fixed_hour": FIXED_HOUR, "n_cal": N_CAL, "n_eval": N_EVAL, "reps": REPS},
           "profile_formula": form,
           "base_200reps": {f"{t}_{meth}": {k: round(float(v), 2) for k, v in m.loc[(t, meth)].items()}
                            for t in TYPES for meth in ["A", "B", "C"]},
           "peak_info_200reps": {t: {k: round(float(v), 3) for k, v in info.loc[t].items()} for t in TYPES},
           "grid_info": {"cases": int(len(grid)), "reps_each": 50},
           "grid_range": {c: rng_of(c) for c in grid.columns if c.endswith("_pct")},
           "grid_range_scale1": {c: [float(grid[grid.scale == 1.0][c].min()), float(grid[grid.scale == 1.0][c].max())]
                                 for c in grid.columns if c.endswith("_pct")},
           "grid_range_scale01": {c: [float(grid[grid.scale == 0.1][c].min()), float(grid[grid.scale == 0.1][c].max())]
                                  for c in grid.columns if c.endswith("_pct")},
           "grid_event_A_by_spike": {str(sp): [float(grid[grid.spike == sp]["催しの日_A_mean_err_pct"].min()),
                                               float(grid[grid.spike == sp]["催しの日_A_mean_err_pct"].max())]
                                     for sp in [0.05, 0.15, 0.30]},
           "grid_weekend_A_low_noise_scale1": [float(g["土日_A_mean_err_pct"].min()), float(g["土日_A_mean_err_pct"].max())]
           if (g := grid[(grid.hour_sd == 0.05) & (grid.scale == 1.0)]) is not None else None,
           "n_calibration": cal.to_dict("records"),
           "n_calibration_range": {"B_mean_err_pct": [float(cal.B_mean_err_pct.min()), float(cal.B_mean_err_pct.max())],
                                   "B_within10_pct": [float(cal.B_within10_pct.min()), float(cal.B_within10_pct.max())],
                                   "event_A_mean_err_pct": [float(cal[cal.type == "催しの日"].A_mean_err_pct.min()),
                                                            float(cal[cal.type == "催しの日"].A_mean_err_pct.max())]}}
    json.dump(out, open(RES / "a997_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：時間ごとの割合の形（作成者が置いたもの）
    fig, ax = plt.subplots(figsize=(7.4, 3.9))
    for t, c, mk in [("平日", BLUE, "o"), ("土日", GREEN, "s"), ("催しの日", ORANGE, "^")]:
        ax.plot(HOURS, prof[t] * 100, color=c, marker=mk, lw=2,
                label=f"{t}（ピーク{prof[t].max() * 100:.1f}%、係数の目安{1 / prof[t].max():.2f}）")
    ax.set_xticks(HOURS); ax.set_xticklabels([f"{h}時" for h in HOURS], fontsize=9)
    ax.set_xlabel("時間帯（その時台に入館した人）"); ax.set_ylabel("1日の人数に占める割合（%）")
    ax.set_ylim(0, 31)
    ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    ax.set_title("日の種類ごとの、時間ごとの入館の割合（作成者が置いた形）", fontsize=12)
    save(fig, "a997_profiles.png", SRC)

    # 図2：見込みのずれ（日の種類×見込み方、200回の平均と10〜90%）
    fig, ax = plt.subplots(figsize=(7.6, 4.0))
    meths = [("A", "A ピーク×平日の係数", ORANGE), ("B", "B ピーク×日の種類ごとの係数", BLUE), ("C", "C 13時台×平日の係数", GRAY)]
    x = np.arange(3); bw = 0.26
    for j, (k, lab, c) in enumerate(meths):
        v = [m.loc[(t, k), "mean_err_pct"] for t in TYPES]
        lo = [m.loc[(t, k), "p10_err_pct"] for t in TYPES]
        hi = [m.loc[(t, k), "p90_err_pct"] for t in TYPES]
        xx = x + (j - 1) * bw
        ax.bar(xx, v, bw, color=c, label=lab)
        ax.vlines(xx, lo, hi, color=INK, lw=1)
        for xi, vi, hii in zip(xx, v, hi):
            ax.text(xi, max(vi, hii) + 3, f"{vi:+.0f}%", ha="center", fontsize=8)
    ax.axhline(0, color=INK, lw=0.8)
    ax.set_xticks(x); ax.set_xticklabels(TYPES)
    ax.set_ylabel("見込み÷本当の1日の人数−1（%）")
    ax.set_ylim(-45, 150)
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    ax.set_title("ピークの1時間からの見込みは、日の種類で大きくずれる\n（200回の平均。線は日ごとの10〜90%）", fontsize=12)
    save(fig, "a997_error.png", SRC)

    # 図3：確かめ。Aの催しの日のずれ（ショーの集まり方×時間ごとの振れ、館の大きさ1倍）と、Bの±10%に入る割合
    fig, axes = plt.subplots(1, 2, figsize=(8.2, 3.8))
    ax = axes[0]
    for hs, c in [(0.05, LIGHT), (0.1, BLUE), (0.2, ORANGE)]:
        gg = grid[(grid.hour_sd == hs) & (grid.scale == 1.0)]
        ax.plot(gg.spike * 100, gg["催しの日_A_mean_err_pct"], marker="o", color=c, label=f"時間ごとの振れ {hs}")
    ax.set_xlabel("ショーに集まる割合（%）"); ax.set_ylabel("A 催しの日の見込みのずれ（%）")
    ax.set_xticks([5, 15, 30]); ax.legend(frameon=False, fontsize=8)
    ax.set_title("催しの日（Aの見込み）", fontsize=11)
    ax = axes[1]
    xs = np.arange(3); bw = 0.38
    for j, (sc, c) in enumerate([(1.0, BLUE), (0.1, ORANGE)]):
        gg = grid[(grid.spike == SPIKE) & (grid.scale == sc)]
        ax.bar(xs + (j - 0.5) * bw, gg["平日_B_within10_pct"], bw, color=c,
               label="1日 平均3,000人（基本）" if sc == 1.0 else "1日 平均300人（小さな館）")
        for xi, v in zip(xs + (j - 0.5) * bw, gg["平日_B_within10_pct"]):
            ax.text(xi, v + 1.5, f"{v:.0f}%", ha="center", fontsize=8)
    ax.set_xticks(xs); ax.set_xticklabels(["振れ 0.05", "振れ 0.1", "振れ 0.2"])
    ax.set_ylabel("B 平日で±10%に入った日（%）"); ax.set_ylim(0, 110)
    ax.legend(frameon=False, fontsize=8, loc="upper right")
    ax.set_title("平日（Bの見込み）", fontsize=11)
    fig.suptitle("確かめ：置き方を変えると（各50回）", fontsize=12)
    fig.tight_layout()
    save(fig, "a997_grid.png", SRC)

    print(json.dumps({k: out[k] for k in ["profile_formula", "base_200reps", "peak_info_200reps"]}, ensure_ascii=False, indent=1))
    print(grid.to_string()); print(cal.to_string())


if __name__ == "__main__":
    main()

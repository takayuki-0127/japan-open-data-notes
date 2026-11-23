"""1038 「最短の道」は、毎日同じなのか？（架空のデータ）

架空の通勤（家から職場まで、車で通う道が4本）。道ごとの本当の平均の時間を作成者が置き、
日ごとの時間は「その日の町全体の混み方（4本に共通）」と「道ごとのその日の振れ」で決まる。
平均でいちばん速い道が、その日いちばん速い道になる日は何%か、前の日に速かった道に乗りかえると得か、を数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1038
SRC = "架空の通勤の道4本（作成者が乱数で作成、seed 1038）"
ROUTES = ["道A", "道B", "道C", "道D"]
MEAN = np.array([31.0, 30.0, 32.0, 33.0])      # 本当の平均（分）
NOISE = np.array([1.5, 4.0, 2.5, 3.0])         # 道ごとのその日の振れ（標準偏差、分）
LOAD = np.array([3.0, 1.0, 2.0, 0.5])          # 町全体の混み方1つ分で増える分
N_DAYS = 250        # 1年の通勤日
N_YEARS = 400       # 作り直す回数
N_REC = 10          # 最初に記録する日数


def make_days(rng, n_days, n_years, mean=MEAN, noise=NOISE, load=LOAD, phi=0.0, phi_c=0.0):
    """返り値：時間（年, 日, 道）、町全体の混み方（年, 日）
    phi：道ごとの振れが次の日に残る度合い（AR(1) の係数）。phi_c：町全体の混み方が残る度合い。
    どちらも、1日あたりの振れの大きさ（標準偏差）は変えない。"""
    k = len(mean)
    c = np.empty((n_years, n_days)); e = np.empty((n_years, n_days, k))
    zc = rng.standard_normal((n_years, n_days)); ze = rng.standard_normal((n_years, n_days, k))
    c[:, 0] = zc[:, 0]; e[:, 0] = ze[:, 0]
    for d in range(1, n_days):
        c[:, d] = phi_c * c[:, d - 1] + np.sqrt(1 - phi_c ** 2) * zc[:, d]
        e[:, d] = phi * e[:, d - 1] + np.sqrt(1 - phi ** 2) * ze[:, d]
    t = mean[None, None, :] + load[None, None, :] * c[:, :, None] + noise[None, None, :] * e
    return np.maximum(t, 10.0), c


def strategies(t, n_rec=N_REC, true_mean=MEAN):
    """4つの選び方の、記録の日（最初の n_rec 日）より後の1日あたりの時間"""
    ny, nd, k = t.shape
    days = slice(n_rec, nd)
    best_true = int(np.argmin(true_mean))
    fixed_true = t[:, days, best_true]
    pick_rec = np.argmin(t[:, :n_rec, :].mean(1), axis=1)                     # 最初の10日の平均で選んで固定
    fixed_rec = np.take_along_axis(t[:, days, :], pick_rec[:, None, None], 2)[:, :, 0]
    yest = np.argmin(t[:, n_rec - 1:nd - 1, :], axis=2)                       # 前の日にいちばん速かった道
    follow = np.take_along_axis(t[:, days, :], yest[:, :, None], 2)[:, :, 0]
    oracle = t[:, days, :].min(2)                                             # その日いちばん速い道（後から分かる）
    out = {"平均で最短の道に固定（本当の平均）": fixed_true,
           f"最初の{n_rec}日の平均で選んで固定": fixed_rec,
           "前の日にいちばん速かった道": follow,
           "その日いちばん速い道（後から分かる）": oracle}
    return out, pick_rec, best_true


def summarize(out):
    oracle = out["その日いちばん速い道（後から分かる）"]
    rows = []
    for name, v in out.items():
        rows.append({"strategy": name, "mean_min": round(float(v.mean()), 3),
                     "p90_min": round(float(np.quantile(v, .9)), 3),
                     "over_oracle_min": round(float((v - oracle).mean()), 3),
                     "share_over_5min": round(float(((v - oracle) > 5).mean()) * 100, 2)})
    return rows


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    t, c = make_days(rng, N_DAYS, N_YEARS)
    k = len(ROUTES)
    fastest = t.argmin(2)

    # 例の1年（data）
    ex = pd.DataFrame({"day": np.arange(1, N_DAYS + 1), "town_load": np.round(c[0], 4)})
    for j, r in enumerate(["A", "B", "C", "D"]):
        ex[f"min_{r}"] = np.round(t[0, :, j], 3)
    ex["fastest"] = [ROUTES[i] for i in fastest[0]]
    ex.to_csv(DATA / "days_example_year.csv", index=False)

    # 1) 道ごとの、いちばん速かった日の割合・平均・標準偏差
    share = [(fastest == j).mean() for j in range(k)]
    route_rows = [{"route": ROUTES[j], "true_mean": float(MEAN[j]), "data_mean": round(float(t[:, :, j].mean()), 3),
                   "data_sd": round(float(t[:, :, j].std()), 3),
                   "share_fastest_pct": round(float(share[j]) * 100, 2),
                   "share_fastest_example_year_pct": round(float((fastest[0] == j).mean()) * 100, 2)}
                  for j in range(k)]
    pd.DataFrame(route_rows).to_csv(RES / "routes.csv", index=False)
    same_as_yest = float((fastest[:, 1:] == fastest[:, :-1]).mean())
    expected_same = float(sum(s ** 2 for s in share))  # 日どうしが独立なら、この値（式）
    # 連続して同じ道が最速だった日数（例の1年）
    runs = []
    for y in range(N_YEARS):
        f = fastest[y]; br = np.flatnonzero(np.diff(f) != 0)
        runs.append(np.diff(np.r_[-1, br, N_DAYS - 1]))
    runs = np.concatenate(runs)
    # 平均で最短の道Bが、ほかの道より5分以上遅かった日
    b = t[:, :, 1]; other_min = np.delete(t, 1, axis=2).min(2)
    b_slower5 = float(((b - other_min) > 5).mean())

    # 2) 選び方の比べ（基本）
    out, pick_rec, best_true = strategies(t)
    strat = summarize(out)
    pick_share = {ROUTES[j]: round(float((pick_rec == j).mean()) * 100, 2) for j in range(k)}
    pd.DataFrame(strat).to_csv(RES / "strategies_base.csv", index=False)

    # 3) 確かめ：道ごとの振れが次の日に残る度合い（phi）、町全体の混み方が残る度合い
    sens = []
    for phi in [0.0, 0.5, 0.8, 0.95]:
        tt, _ = make_days(np.random.default_rng(SEED * 10 + int(phi * 100)), N_DAYS, 200, phi=phi)
        o, _, _ = strategies(tt)
        s = {r["strategy"]: r for r in summarize(o)}
        ff = tt.argmin(2)
        sens.append({"change": "道ごとの振れが次の日に残る度合い", "value": phi,
                     "share_B_fastest_pct": round(float((ff == 1).mean()) * 100, 2),
                     "same_as_yesterday_pct": round(float((ff[:, 1:] == ff[:, :-1]).mean()) * 100, 2),
                     **{f"mean_{i}": s[n]["mean_min"] for i, n in enumerate(o)}})
    for phi_c in [0.5, 0.9]:
        tt, _ = make_days(np.random.default_rng(SEED * 20 + int(phi_c * 100)), N_DAYS, 200, phi_c=phi_c)
        o, _, _ = strategies(tt)
        s = {r["strategy"]: r for r in summarize(o)}
        ff = tt.argmin(2)
        sens.append({"change": "町全体の混み方が次の日に残る度合い", "value": phi_c,
                     "share_B_fastest_pct": round(float((ff == 1).mean()) * 100, 2),
                     "same_as_yesterday_pct": round(float((ff[:, 1:] == ff[:, :-1]).mean()) * 100, 2),
                     **{f"mean_{i}": s[n]["mean_min"] for i, n in enumerate(o)}})
    # 道の振れの大きさ（倍率）
    for sc in [0.5, 2.0]:
        tt, _ = make_days(np.random.default_rng(SEED * 30 + int(sc * 10)), N_DAYS, 200, noise=NOISE * sc)
        o, _, _ = strategies(tt)
        s = {r["strategy"]: r for r in summarize(o)}
        ff = tt.argmin(2)
        sens.append({"change": "道ごとの振れの大きさ（倍）", "value": sc,
                     "share_B_fastest_pct": round(float((ff == 1).mean()) * 100, 2),
                     "same_as_yesterday_pct": round(float((ff[:, 1:] == ff[:, :-1]).mean()) * 100, 2),
                     **{f"mean_{i}": s[n]["mean_min"] for i, n in enumerate(o)}})
    # 道Bの平均と2番目（道A）の差
    for mb in [28.0, 30.8]:
        mm = MEAN.copy(); mm[1] = mb
        tt, _ = make_days(np.random.default_rng(SEED * 40 + int(mb * 10)), N_DAYS, 200, mean=mm)
        o, _, _ = strategies(tt, true_mean=mm)
        s = {r["strategy"]: r for r in summarize(o)}
        ff = tt.argmin(2)
        sens.append({"change": "道Bの本当の平均（分、道Aは31分）", "value": mb,
                     "share_B_fastest_pct": round(float((ff == 1).mean()) * 100, 2),
                     "same_as_yesterday_pct": round(float((ff[:, 1:] == ff[:, :-1]).mean()) * 100, 2),
                     **{f"mean_{i}": s[n]["mean_min"] for i, n in enumerate(o)}})
    sens_df = pd.DataFrame(sens)
    names = list(out.keys())
    sens_df["follow_minus_fixed_min"] = (sens_df["mean_2"] - sens_df["mean_0"]).round(3)
    sens_df["rec_minus_fixed_min"] = (sens_df["mean_1"] - sens_df["mean_0"]).round(3)
    sens_df.to_csv(RES / "sensitivity.csv", index=False)

    base = {r["strategy"]: r for r in strat}
    res = {
        "setup": {"routes": ROUTES, "true_mean_min": MEAN.tolist(), "noise_sd_min": NOISE.tolist(),
                  "town_load_coef": LOAD.tolist(), "days_per_year": N_DAYS, "years": N_YEARS, "record_days": N_REC,
                  "strategy_names": names},
        "routes": route_rows,
        "best_true_route": ROUTES[best_true],
        "share_best_route_fastest_pct": round(float(share[1]) * 100, 2),
        "share_best_route_not_fastest_pct": round(float(1 - share[1]) * 100, 2),
        "same_fastest_as_yesterday_pct": round(same_as_yest * 100, 2),
        "same_fastest_if_independent_formula_pct": round(expected_same * 100, 2),
        "run_length_mean_days": round(float(runs.mean()), 3),
        "run_length_max_days": int(runs.max()),
        "share_run_1day_pct": round(float((runs == 1).mean()) * 100, 2),
        "B_slower_than_best_other_by_5min_pct": round(b_slower5 * 100, 2),
        "strategies_base": strat,
        "record10_pick_share_pct": pick_share,
        "follow_minus_fixed_min": round(base[names[2]]["mean_min"] - base[names[0]]["mean_min"], 3),
        "rec_minus_fixed_min": round(base[names[1]]["mean_min"] - base[names[0]]["mean_min"], 3),
        "fixed_minus_oracle_min": round(base[names[0]]["mean_min"] - base[names[3]]["mean_min"], 3),
        "sensitivity": sens_df.to_dict("records"),
        "sens_range_share_B_fastest_pct": [float(sens_df.share_B_fastest_pct.min()), float(sens_df.share_B_fastest_pct.max())],
        "sens_range_follow_minus_fixed_min": [float(sens_df.follow_minus_fixed_min.min()), float(sens_df.follow_minus_fixed_min.max())],
    }

    # 図1：例の1年、日ごとにいちばん速かった道
    fig, ax = plt.subplots(figsize=(7.4, 2.9))
    cols = [BLUE, ORANGE, GREEN, GRAY]
    for j in range(k):
        dd = np.flatnonzero(fastest[0] == j)
        ax.scatter(dd + 1, np.full(len(dd), j), s=9, color=cols[j], marker="s", lw=0)
    ax.set_yticks(range(k)); ax.set_yticklabels([f"{r}（平均{m:.0f}分）" for r, m in zip(ROUTES, MEAN)])
    ax.invert_yaxis(); ax.set_xlabel("通勤日（例の1年、250日）"); ax.set_xlim(0, N_DAYS + 1)
    ax.set_title(f"いちばん速かった道は毎日入れかわる（平均最短の道Bは{route_rows[1]['share_fastest_example_year_pct']:.0f}%の日）")
    save(fig, "a1038_example_year.png", SRC, y=-0.03)

    # 図2：選び方ごとの1日あたりの時間
    fig, ax = plt.subplots(figsize=(7.4, 3.4))
    labels = [r["strategy"] for r in strat][::-1]
    vals = [r["mean_min"] for r in strat][::-1]
    fixed = strat[0]["mean_min"]
    diffs = [round(v - fixed, 3) for v in vals]
    ax.barh(labels, diffs, color=[GRAY, ORANGE, LIGHT, BLUE])
    ax.axvline(0, color=INK, lw=.8)
    for i, (v, d) in enumerate(zip(vals, diffs)):
        ax.text(d + (0.06 if d >= 0 else -0.06), i, f"{d:+.3f}分（{v:.3f}分）", va="center",
                ha="left" if d >= 0 else "right", fontsize=9)
    ax.set_xlim(-3.2, 2.0)
    ax.set_xlabel("平均で最短の道に固定したとき（29.996分）との差（分、1日あたり、11日目以降、400年）。括弧は1日の平均")
    ax.set_title("前の日に速かった道へ乗りかえると、固定より遅くなった（基本の置き方）")
    save(fig, "a1038_strategies.png", SRC, y=-0.05)

    # 図3：振れが次の日に残る度合いと、乗りかえの得失
    ss = sens_df[sens_df.change == "道ごとの振れが次の日に残る度合い"]
    fig, ax = plt.subplots(figsize=(7.4, 3.6))
    ax.plot(ss.value, ss.follow_minus_fixed_min, "o-", color=ORANGE, label="前の日に速かった道 − 平均最短の道に固定")
    ax.plot(ss.value, ss.rec_minus_fixed_min, "s-", color=BLUE, label="最初の10日で選んで固定 − 平均最短の道に固定")
    ax.axhline(0, color=GRAY, lw=1)
    for x, y in zip(ss.value, ss.follow_minus_fixed_min):
        ax.text(x, y + 0.12, f"{y:+.2f}分", ha="center", fontsize=8.5, color=ORANGE)
    ax.set_xlabel("道ごとの振れが次の日に残る度合い（0＝毎日でたらめ、0.95＝何日も続く）")
    ax.set_ylabel("1日あたりの差（分）")
    ax.set_ylim(min(-1.6, ss.follow_minus_fixed_min.min() - 0.4), max(1.4, ss.follow_minus_fixed_min.max() + 0.5))
    ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    ax.set_title("振れが次の日に残ると、前の日の最速への乗りかえは損から得に変わった")
    save(fig, "a1038_persistence.png", SRC, y=-0.05)

    json.dump(res, open(RES / "a1038_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()

"""878 混雑の予測を出すと、空いている時間に人が集まって外れるのか？（架空のデータ）

架空のテーマパークの人気の乗り物（9時〜21時、1時間に600人乗れる）。乗りたい人は1日平均6,600人で、
それぞれ「行きたい時刻」がある（昼に多い）。時間帯ごとの予想待ち時間を出すと、予測を見た人の一部が
前後数時間のうち、予想待ち＋ずらす手間がいちばん小さい時刻に移る。その結果、実際の待ちと予測がどれだけずれるかを数える。
待ち時間は、1時間ごとの人数と乗れる人数から、列の長さを流れとして計算する（1時間の中のばらつきは入れない）。
"""
import json, time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 878
SRC = "架空のテーマパークの乗り物（作成者が乱数で作成、seed 878）"
HOURS = np.arange(9, 21)                 # 9時台〜20時台の12枠
H = len(HOURS)
CAP = 600.0
N_MEAN = 6600
PROFILE = np.array([3, 6, 9, 11, 12, 12, 11, 9, 7, 5, 3, 2], float); PROFILE /= PROFILE.sum()
SHIFT_COST = 10.0                        # 1時間ずらす手間を、待ち10分ぶんと置く


def waits(arr):
    """1時間ごとの到着人数 → その時間帯に来た人の平均の待ち（分）。列の長さを流れで計算"""
    q_prev, w = 0.0, np.empty(H)
    for t in range(H):
        q = max(0.0, q_prev + arr[t] - CAP)
        w[t] = 60.0 * (q_prev + q) / 2.0 / CAP
        q_prev = q
    return w


def choice_matrix(fc, flex, tau):
    """行きたい時刻 h の人（予測を見た人）が、時刻 k を選ぶ確率。tau=0 はいちばん小さい所に全員"""
    P = np.zeros((H, H))
    for h in range(H):
        ks = np.arange(max(0, h - flex), min(H, h + flex + 1))
        cost = fc[ks] + SHIFT_COST * np.abs(ks - h)
        if tau == 0:
            P[h, ks[np.argmin(cost)]] = 1.0
        else:
            u = np.exp(-(cost - cost.min()) / tau); P[h, ks] = u / u.sum()
    return P


def one_day(rng, fc, share, flex, tau):
    n = rng.poisson(N_MEAN)
    pref = rng.multinomial(n, PROFILE)
    if fc is None or share == 0:
        return pref.astype(float), pref
    seers = rng.binomial(pref, share)
    P = choice_matrix(fc, flex, tau)
    arr = (pref - seers).astype(float)
    for h in range(H):
        if seers[h]:
            arr += rng.multinomial(seers[h], P[h])
    return arr, pref


def expected_arr(fc, share, flex, tau):
    exp_pref = N_MEAN * PROFILE
    if fc is None:
        return exp_pref
    return exp_pref * (1 - share) + (exp_pref * share) @ choice_matrix(fc, flex, tau)


def forecast_fixed_point(share, flex, tau, iters=400):
    """人の動きを織り込んだ予測：予測→人の動き→待ち、を少しずつ混ぜて繰り返す"""
    fc = waits(N_MEAN * PROFILE)
    for i in range(iters):
        fc = fc + (waits(expected_arr(fc, share, flex, tau)) - fc) / (i + 2)
    return fc


def run(seed, share=0.4, flex=2, tau=0.0, reps=30, days=60, burn=10):
    """4つの出し方を、同じ乱数の流れで比べる。reps 回 × days 日、最初の burn 日は数えない"""
    fc_naive = waits(N_MEAN * PROFILE)                       # 人が動く前の混み方（だれも予測を見ないとき）
    fc_fp = forecast_fixed_point(share, flex, tau)
    res = {}
    for kind in ["none", "naive", "yesterday", "fixed_point"]:
        rng = np.random.default_rng(seed)
        mw, mae, peak, low3_gap, fcs, acts = [], [], [], [], [], []
        for r in range(reps):
            fc = fc_naive.copy()
            for d in range(days):
                use = None if kind == "none" else (fc_fp if kind == "fixed_point" else fc)
                arr, pref = one_day(rng, use, share, flex, tau)
                w = waits(arr)
                if d >= burn:
                    mw.append(float((w * arr).sum() / arr.sum())); peak.append(float(w.max()))
                    if use is not None:
                        mae.append(float(np.abs(w - use).mean()))
                        gain = arr > pref                            # 人が移ってきた時間帯
                        if gain.any():
                            low3_gap.append(float((w[gain] - use[gain]).mean()))
                        if r == 0:
                            fcs.append(use.copy()); acts.append(w.copy())
                    else:
                        mae.append(float(np.abs(w - fc_naive).mean()))   # だれも動かないときの、日ごとの揺れの分の外れ
                        if r == 0:
                            acts.append(w.copy())
                if kind == "yesterday":
                    fc = w
        res[kind] = {"mean_wait": float(np.mean(mw)), "peak_wait": float(np.mean(peak)),
                     "mae": float(np.mean(mae)) if mae else None,
                     "inflow_actual_minus_forecast": float(np.mean(low3_gap)) if low3_gap else None,
                     "fc_example": np.array(fcs) if fcs else None, "act_example": np.array(acts)}
    res["fc_naive"] = fc_naive; res["fc_fp"] = fc_fp
    return res


KIND_JA = {"none": "予測を出さない", "naive": "人が動く前の混み方をそのまま予測にする",
           "yesterday": "前日の実際の待ちを予測にする", "fixed_point": "人の動きを織り込んだ予測"}


def rd(x, k=2):
    return None if x is None else round(float(x), k)


def main():
    t0 = time.time()
    # 1) 基本：予測を見る人4割、前後2時間まで、いちばん小さい所を選ぶ
    base = run(SEED * 10)
    rows = []
    for k in KIND_JA:
        b = base[k]
        rows.append({"forecast": KIND_JA[k], "mean_wait_min": rd(b["mean_wait"]), "peak_wait_min": rd(b["peak_wait"]),
                     "mae_min": rd(b["mae"]), "inflow_actual_minus_forecast_min": rd(b["inflow_actual_minus_forecast"])})
    bdf = pd.DataFrame(rows); bdf.to_csv(RES / "base_forecasts.csv", index=False)

    # 時間帯ごとの平均（例の1回目・数えた50日の平均）
    hr = pd.DataFrame({"hour": HOURS, "forecast_naive": np.round(base["fc_naive"], 2),
                       "actual_none": np.round(base["none"]["act_example"].mean(0), 2),
                       "actual_naive": np.round(base["naive"]["act_example"].mean(0), 2),
                       "forecast_fixed_point": np.round(base["fc_fp"], 2),
                       "actual_fixed_point": np.round(base["fixed_point"]["act_example"].mean(0), 2)})
    hr.to_csv(RES / "by_hour_base.csv", index=False)
    yd = pd.DataFrame(base["yesterday"]["act_example"][:20], columns=[f"h{h}" for h in HOURS]).round(2)
    yd.insert(0, "day", np.arange(11, 31)); yd.to_csv(RES / "yesterday_days11_30.csv", index=False)

    # data：1日分（予測を見た人の行きたい時刻と、実際に行った時刻）
    rng = np.random.default_rng(SEED)
    arr_none, pref = one_day(rng, None, 0.4, 2, 0.0)
    rng = np.random.default_rng(SEED)
    arr_naive, pref2 = one_day(rng, base["fc_naive"], 0.4, 2, 0.0)
    pd.DataFrame({"hour": HOURS, "preferred": pref2, "arrivals_no_forecast": arr_none.astype(int),
                  "arrivals_naive_forecast": arr_naive.astype(int), "capacity": int(CAP),
                  "wait_no_forecast": np.round(waits(arr_none), 3), "wait_naive_forecast": np.round(waits(arr_naive), 3),
                  "forecast_naive": np.round(base["fc_naive"], 3)}).to_csv(DATA / "one_day.csv", index=False)

    # 2) 確かめ：見る人の割合×選び方の揺らぎ×ずらせる幅（各10回×60日）
    sens = []
    combos = [(s, tau, 2) for s in (0.1, 0.2, 0.4, 0.6) for tau in (0.0, 5.0, 15.0)] + \
             [(0.4, 0.0, f) for f in (1, 3)] + [(0.4, 5.0, f) for f in (1, 3)]
    for i, (s, tau, f) in enumerate(combos):
        o = run(SEED * 100 + i, s, f, tau, reps=10)
        row = {"share_seeing": s, "tau": tau, "flex_hours": f}
        for k in KIND_JA:
            row[f"{k}_mean_wait"] = rd(o[k]["mean_wait"]); row[f"{k}_peak"] = rd(o[k]["peak_wait"])
            row[f"{k}_mae"] = rd(o[k]["mae"])
            if k != "none":
                row[f"{k}_inflow_gap"] = rd(o[k]["inflow_actual_minus_forecast"])
        sens.append(row)
    sdf = pd.DataFrame(sens); sdf.to_csv(RES / "sensitivity.csv", index=False)

    out = {"setting": {"hours": "9時台〜20時台の12枠", "capacity_per_hour": CAP, "visitors_mean": N_MEAN,
                       "profile": [round(float(x), 4) for x in PROFILE], "share_seeing": 0.4, "flex_hours": 2,
                       "tau": 0.0, "shift_cost_min_per_hour": SHIFT_COST, "reps": 30, "days": 60, "burn_in": 10},
           "base": {k: {"mean_wait": rd(base[k]["mean_wait"]), "peak_wait": rd(base[k]["peak_wait"]),
                        "mae": rd(base[k]["mae"]), "inflow_actual_minus_forecast": rd(base[k]["inflow_actual_minus_forecast"])}
                    for k in KIND_JA},
           "naive_mae_range_sens": [float(sdf.naive_mae.min()), float(sdf.naive_mae.max())],
           "naive_inflow_gap_range_sens": [float(sdf.naive_inflow_gap.min()), float(sdf.naive_inflow_gap.max())],
           "fixed_point_inflow_gap_range_sens": [float(sdf.fixed_point_inflow_gap.min()), float(sdf.fixed_point_inflow_gap.max())],
           "fixed_point_mean_wait_range_sens": [float(sdf.fixed_point_mean_wait.min()), float(sdf.fixed_point_mean_wait.max())],
           "none_mean_wait_range_sens": [float(sdf.none_mean_wait.min()), float(sdf.none_mean_wait.max())],
           "naive_mean_wait_range_sens": [float(sdf.naive_mean_wait.min()), float(sdf.naive_mean_wait.max())],
           "share_cases_yesterday_worse_than_none": round(float((sdf.yesterday_mean_wait > sdf.none_mean_wait).mean()), 3),
           "fixed_point_mae_range_sens": [float(sdf.fixed_point_mae.min()), float(sdf.fixed_point_mae.max())],
           "n_cases_sens": int(len(sdf)),
           "none_mae_range_sens": [float(sdf.none_mae.min()), float(sdf.none_mae.max())],
           "fixed_point_mae_range_tau_pos": [float(sdf[sdf.tau > 0].fixed_point_mae.min()), float(sdf[sdf.tau > 0].fixed_point_mae.max())],
           "fixed_point_mae_range_tau0": [float(sdf[sdf.tau == 0].fixed_point_mae.min()), float(sdf[sdf.tau == 0].fixed_point_mae.max())],
           "naive_minus_none_mean_wait_range": [round(float((sdf.naive_mean_wait - sdf.none_mean_wait).min()), 2),
                                               round(float((sdf.naive_mean_wait - sdf.none_mean_wait).max()), 2)],
           "share_cases_naive_worse_than_none": round(float((sdf.naive_mean_wait > sdf.none_mean_wait).mean()), 3),
           "share_cases_fp_worse_than_none": round(float((sdf.fixed_point_mean_wait > sdf.none_mean_wait).mean()), 3)}
    json.dump(out, open(RES / "a878_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：人が動く前の予測と、出したあとの実際（時間帯ごと）
    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    x = HOURS
    ax.plot(x, hr.actual_none, color=GRAY, lw=2, ls="--", label="予測を出さないときの実際")
    ax.plot(x, hr.forecast_naive, color=BLUE, lw=2, marker="o", ms=4, label="出した予測（人が動く前の混み方）")
    ax.plot(x, hr.actual_naive, color=ORANGE, lw=2.4, marker="o", ms=4, label="予測を出したあとの実際")
    ax.set_xticks(x); ax.set_xticklabels([f"{h}時" for h in x], fontsize=9)
    ax.set_ylabel("その時間帯に来た人の平均の待ち（分）"); ax.legend(frameon=False, fontsize=9, loc="upper right")
    ax.set_ylim(0, max(hr.actual_naive.max(), hr.forecast_naive.max()) * 1.3)
    ax.set_title("4割がいちばん空く時刻へ移ると、空くはずの時間帯が混む")
    save(fig, "a878_by_hour.png", SRC)

    # 図2：前日の実際を予測にすると（11〜30日目、時間帯ごとの待ち）
    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    for col, h, c in [("h12", 12, BLUE), ("h15", 15, ORANGE), ("h17", 17, GREEN)]:
        ax.plot(yd.day, yd[col], marker="o", ms=3.5, lw=1.8, color=c, label=f"{h}時台")
    ax.set_xlabel("日目（前日の実際の待ちを、その日の予測として出す）"); ax.set_ylabel("実際の平均の待ち（分）")
    ax.legend(frameon=False, fontsize=9, ncol=3, loc="upper right"); ax.set_ylim(0, None)
    ax.set_xticks(np.arange(11, 31, 2))
    ax.set_title("前日の待ちを予測にすると、空く時間帯が日ごとに入れ替わる")
    save(fig, "a878_yesterday.png", SRC)

    # 図3：確かめ（予測の外れ：人が動く前の予測、見る人の割合×揺らぎ）
    s2 = sdf[sdf.flex_hours == 2]
    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    for tau, c, lab in [(0.0, ORANGE, "全員がいちばん小さい時刻を選ぶ"), (5.0, BLUE, "揺らぎ小（5分）"),
                        (15.0, LIGHT, "揺らぎ大（15分）")]:
        d = s2[s2.tau == tau].sort_values("share_seeing")
        ax.plot(d.share_seeing * 100, d.naive_mae, "o-", color=c, lw=2, label=lab)
        ax.plot(d.share_seeing * 100, d.fixed_point_mae, "s:", color=c, lw=1.5)
    ax.plot([], [], "k-", lw=1.5, label="実線：人が動く前の混み方の予測"); ax.plot([], [], "k:", lw=1.5, label="点線：人の動きを織り込んだ予測")
    ax.set_xlabel("予測を見て動く人の割合（%）"); ax.set_ylabel("予測の外れ（時間帯ごとの差の平均、分）")
    ax.set_xticks([10, 20, 40, 60]); ax.legend(frameon=False, fontsize=8.5); ax.set_ylim(0, None)
    ax.set_title("見る人が多く、選び方がそろうほど、予測は外れる（各10回×60日）")
    save(fig, "a878_sensitivity.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1)); print(bdf.to_string()); print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()

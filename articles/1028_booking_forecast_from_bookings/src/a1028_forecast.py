"""1028 予約の数から当日の人数を見込むと、どれだけ外れるのか？（架空のデータ）

架空の宿。3年分の毎日の予約（1件ごと）を作る。1日の予約の組数の平均は、基本25組×曜日の重み×季節の波
×日ごとの振れ（ガンマ分布）。組の人数は1〜4人。1件の予約が何日前に入るかは幾何分布（平均 m 日）、
予約は12%が取り消し（取り消す日は、予約した日と泊まる日のあいだで一様）、残りの3%が無断で来ない。
当日の人数＝取り消さず、無断でもなく来た組の人数（飛び込みの客はない）。
3年目の毎日について、L 日前の時点の予約の人数から当日の人数を4つのやり方で見込み、外れを数える。
  ① そのまま（L 日前の予約の人数＝当日の人数）
  ② 倍率（過去2年の同じ曜日の「当日÷L日前」を掛ける）
  ③ 足し算（過去2年の同じ曜日の「当日−L日前」の平均を足す）
  ④ 予約を使わない（1年前と2年前の同じ曜日の日の当日の人数の平均）
3年目に、予約の入り方・取り消し・お客の数が変わった場合も数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1028
SRC = "架空の宿の予約（作成者が乱数で作成、seed 1028）"
R = 60
NDAY = 364 * 3            # 3年（52週×3、曜日がそろう）
WDW = np.array([0.8, 0.8, 0.85, 0.9, 1.3, 1.7, 0.8])
GS = np.array([1, 2, 3, 4]); GP = np.array([0.25, 0.5, 0.1, 0.15])
LEADS = [1, 3, 7, 14, 30, 60]
METHODS = ["①そのまま", "②倍率", "③足し算", "④予約を使わない"]
BASE = {"base": 25.0, "day_cv": 0.15, "lead_mean": 20.0, "cancel": 0.12, "noshow": 0.03}
SCEN = {"基本（3年目も同じ）": {}, "3年目はお客が10%多い": {"demand": 1.10},
        "3年目は予約が早まる（何日前の平均が1.3倍）": {"lead": 1.3}, "3年目は予約が遅くなる（0.75倍）": {"lead": 0.75},
        "3年目は取り消しが18%に増える": {"cancel": 0.18}}


def make_bookings(rng, p, scen):
    """1回分の3年の予約（1件ごと）。3年目だけ scen の変化を入れる"""
    d = np.arange(NDAY)
    y3 = d >= 728
    season = 1 + 0.25 * np.sin(2 * np.pi * (d % 364) / 364)
    mu = p["base"] * WDW[d % 7] * season * np.where(y3, scen.get("demand", 1.0), 1.0)
    k = 1 / p["day_cv"] ** 2
    n = rng.poisson(mu * rng.gamma(k, 1 / k, NDAY))
    day = np.repeat(d, n)
    m = p["lead_mean"] * np.where(day >= 728, scen.get("lead", 1.0), 1.0)
    lead = rng.geometric(1 / (m + 1)) - 1               # 0日前（当日）から
    size = rng.choice(GS, size=len(day), p=GP)
    q = np.where(day >= 728, scen.get("cancel", p["cancel"]), p["cancel"])
    canc = rng.random(len(day)) < q
    c_at = rng.random(len(day)) * lead                  # 何日前に取り消すか（0〜lead）
    noshow = (~canc) & (rng.random(len(day)) < p["noshow"])
    return day, lead, size, canc, c_at, noshow


def daily(day, lead, size, canc, c_at, noshow):
    final = np.bincount(day, weights=size * ((~canc) & (~noshow)), minlength=NDAY)
    otb = {}
    for L in LEADS:
        on = (lead >= L) & ((~canc) | (c_at < L))
        otb[L] = np.bincount(day, weights=size * on, minlength=NDAY)
    return final, otb


def forecast(final, otb):
    d = np.arange(NDAY); wd = d % 7
    hist = d < 728; t = np.arange(728, NDAY)
    out = {}
    for L in LEADS:
        o = otb[L]
        ratio = np.array([final[hist & (wd == w)].sum() / max(o[hist & (wd == w)].sum(), 1e-9) for w in range(7)])
        add = np.array([(final - o)[hist & (wd == w)].mean() for w in range(7)])
        out[L] = {"①そのまま": o[t], "②倍率": o[t] * ratio[wd[t]], "③足し算": o[t] + add[wd[t]],
                  "④予約を使わない": (final[t - 364] + final[t - 728]) / 2}
    return out, final[t]


def run(seed, p, scen, keep=False, reps=None):
    reps = reps or R
    errs = {L: {m: [] for m in METHODS} for L in LEADS}
    acts = []
    for r in range(reps):
        rng = np.random.default_rng(seed + r)
        b = make_bookings(rng, p, scen)
        final, otb = daily(*b)
        fc, act = forecast(final, otb)
        acts.append(act)
        for L in LEADS:
            for mth in METHODS:
                errs[L][mth].append(fc[L][mth])
        if keep and r == 0:
            t = np.arange(728, NDAY)
            one = pd.DataFrame({"day_year3": t - 727, "weekday": t % 7, "final_people": final[t].astype(int),
                                **{f"on_books_L{L}": otb[L][t].astype(int) for L in LEADS},
                                **{f"fc_L7_{m[0]}": np.round(fc[7][m], 2) for m in METHODS}})
    act = np.concatenate(acts)
    rows = []
    for L in LEADS:
        for mth in METHODS:
            f = np.concatenate(errs[L][mth])
            ok = act > 0
            e = (f[ok] - act[ok]) / act[ok]
            rows.append({"lead_L": L, "method": mth, "mape": round(float(np.abs(e).mean()) * 100, 2),
                         "bias_total": round(float(f.sum() / act.sum() - 1) * 100, 2),
                         "share_off_20pct": round(float((np.abs(e) > 0.2).mean()) * 100, 2),
                         "p10": round(float(np.quantile(e, .1)) * 100, 2), "p90": round(float(np.quantile(e, .9)) * 100, 2)})
    df = pd.DataFrame(rows)
    return (df, one) if keep else df


def share_formula(p, L):
    """L 日前の予約の人数 ÷ 当日の人数 の期待値（式）。幾何分布の何日前・一様な取り消し日から"""
    m = p["lead_mean"]; q = p["cancel"]; ns = p["noshow"]
    j = np.arange(0, 3000); pj = (1 / (m + 1)) * (m / (m + 1)) ** j
    sel = j >= L
    keep = np.where(j[sel] > 0, 1 - q * (j[sel] - L) / np.maximum(j[sel], 1), 1 - q * 0)
    num = (pj[sel] * keep).sum()
    return num / ((1 - q) * (1 - ns))


def main():
    t0 = time.time()
    p = BASE
    res = {"setting": {**p, "weekday_weights": WDW.tolist(), "group_size_probs": dict(zip(GS.tolist(), GP.tolist())),
                       "season_amplitude": 0.25, "reps": R, "days_per_year": 364, "leads": LEADS}}
    allr = []
    for i, (sn, sc) in enumerate(SCEN.items()):
        if i == 0:
            df, one = run(SEED * 1000, p, sc, keep=True)
            one.to_csv(DATA / "year3_one_run.csv", index=False)
        else:
            df = run(SEED * 1000 + i * 100, p, sc)
        df.insert(0, "scenario", sn)
        allr.append(df)
    tab = pd.concat(allr, ignore_index=True)
    res["one_run_year3_final_people"] = {"mean": round(float(one.final_people.mean()), 2), "min": int(one.final_people.min()),
                                         "max": int(one.final_people.max())}
    tab.to_csv(RES / "by_scenario_method_lead.csv", index=False)
    base = tab[tab.scenario == "基本（3年目も同じ）"]
    res["base"] = {f"L{r['lead_L']}_{r['method']}": {k: r[k] for k in ["mape", "bias_total", "share_off_20pct", "p10", "p90"]}
                   for r in base.to_dict(orient="records")}
    res["method1_share_formula"] = {str(L): round((share_formula(p, L) - 1) * 100, 2) for L in LEADS}
    res["method1_max_abs_sim_minus_formula_pt"] = round(float(max(abs(base[(base.lead_L == L) & (base.method == "①そのまま")].bias_total.iloc[0]
                                                                     - res["method1_share_formula"][str(L)]) for L in LEADS)), 2)
    # 予約を使う見込み（②③のよいほう）が④より外れの小さい日数前
    best = {}
    for L in LEADS:
        b = base[base.lead_L == L].set_index("method").mape
        best[str(L)] = {"best_booking": round(float(min(b["②倍率"], b["③足し算"])), 2), "no_booking": float(b["④予約を使わない"])}
    res["base_booking_vs_nobooking"] = best
    res["scenarios_L7"] = {sn: {r["method"]: {"mape": r["mape"], "bias_total": r["bias_total"]}
                                for r in tab[(tab.scenario == sn) & (tab.lead_L == 7)].to_dict(orient="records")} for sn in SCEN}
    res["scenarios_L30"] = {sn: {r["method"]: {"mape": r["mape"], "bias_total": r["bias_total"]}
                                 for r in tab[(tab.scenario == sn) & (tab.lead_L == 30)].to_dict(orient="records")} for sn in SCEN}

    # 確かめ：組数×日ごとの振れ×何日前に入るか（27通り、3年目も同じ、各20回）
    grid = []
    j = 0
    for base_n in [10, 25, 60]:
        for cv in [0.05, 0.15, 0.30]:
            for lm in [10, 20, 40]:
                pp = {**p, "base": base_n, "day_cv": cv, "lead_mean": lm}
                df = run(SEED * 100000 + j * 100, pp, {}, reps=20); j += 1
                row = {"base_groups": base_n, "day_cv": cv, "lead_mean": lm}
                for L in [7, 30]:
                    s = df[df.lead_L == L].set_index("method")
                    for mth in METHODS:
                        row[f"L{L}_{mth[0]}_mape"] = float(s.loc[mth, "mape"])
                    row[f"L{L}_①_bias"] = float(s.loc["①そのまま", "bias_total"])
                    row[f"L{L}_①_formula"] = round((share_formula(pp, L) - 1) * 100, 2)
                    row[f"L{L}_best_booking_mape"] = min(row[f"L{L}_②_mape"], row[f"L{L}_③_mape"])
                    row[f"L{L}_booking_beats_nobooking"] = bool(row[f"L{L}_best_booking_mape"] < row[f"L{L}_④_mape"])
                grid.append(row)
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "sensitivity_grid.csv", index=False)
    rg = lambda c: [float(grid[c].min()), float(grid[c].max())]
    res["grid"] = {"n_cases": int(len(grid)),
                   "L7_best_booking_mape": rg("L7_best_booking_mape"), "L7_nobooking_mape": rg("L7_④_mape"),
                   "L7_booking_beats_nobooking": int(grid.L7_booking_beats_nobooking.sum()),
                   "L30_best_booking_mape": rg("L30_best_booking_mape"), "L30_nobooking_mape": rg("L30_④_mape"),
                   "L30_booking_beats_nobooking": int(grid.L30_booking_beats_nobooking.sum()),
                   "L7_method2_mape": rg("L7_②_mape"), "L7_method3_mape": rg("L7_③_mape"),
                   "L30_method2_mape": rg("L30_②_mape"), "L30_method3_mape": rg("L30_③_mape"),
                   "L30_method2_worse_than_nobooking": int((grid["L30_②_mape"] > grid["L30_④_mape"]).sum()),
                   "L30_method3_worse_than_nobooking": int((grid["L30_③_mape"] > grid["L30_④_mape"]).sum()),
                   "L7_method1_bias": rg("L7_①_bias"), "L30_method1_bias": rg("L30_①_bias"),
                   "method1_max_abs_sim_minus_formula_pt": round(float(max((grid["L7_①_bias"] - grid["L7_①_formula"]).abs().max(),
                                                                             (grid["L30_①_bias"] - grid["L30_①_formula"]).abs().max())), 2)}
    with open(RES / "a1028_main.json", "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)

    # 図1：何日前か×やり方ごとの外れ（基本）
    fig, ax = plt.subplots(figsize=(8.4, 4.4))
    for mth, c, mk in zip(METHODS, [GRAY, ORANGE, GREEN, BLUE], ["o", "s", "^", "D"]):
        s = base[base.method == mth]
        if mth.startswith("①"):
            continue
        ax.plot(s.lead_L, s.mape, color=c, marker=mk, ms=5, label=mth, ls="--" if mth.startswith("④") else "-")
    ax.set_xscale("log"); ax.set_xticks(LEADS); ax.set_xticklabels([str(L) for L in LEADS]); ax.minorticks_off()
    ax.set_xlabel("何日前の時点の予約で見込んだか（対数の目盛り）"); ax.set_ylabel("当日の人数からの外れの平均（%）")
    ax.set_ylim(0, None); ax.legend(frameon=False, fontsize=9)
    ax.set_title("近い日は予約で見込むと外れが小さいが、30日前からは倍率のほうが外れる")
    save(fig, "a1028_by_lead.png", SRC)

    # 図2：3年目に変化があったときの、7日前の見込みの多い・少ない（合計どうし）
    fig, ax = plt.subplots(figsize=(8.4, 4.4))
    sns = list(SCEN.keys()); y = np.arange(len(sns)); h = 0.26
    for i, (mth, c) in enumerate(zip(["②倍率", "③足し算", "④予約を使わない"], [ORANGE, GREEN, BLUE])):
        v = [res["scenarios_L7"][sn][mth]["bias_total"] for sn in sns]
        ax.barh(y + (i - 1) * h, v, h, color=c, label=mth)
        for yi, vi in zip(y, v):
            ax.text(vi + (0.4 if vi >= 0 else -0.4), yi + (i - 1) * h, f"{vi:+.1f}", va="center", ha="left" if vi >= 0 else "right", fontsize=8)
    ax.axvline(0, color=INK, lw=.8)
    ax.set_yticks(y); ax.set_yticklabels(sns, fontsize=9); ax.invert_yaxis()
    lim = max(abs(tab[(tab.lead_L == 7) & (tab.method != "①そのまま")].bias_total)) + 4
    ax.set_xlim(-lim, lim)
    ax.set_xlabel("見込みの合計÷当日の人数の合計−1（%、7日前の時点、3年目の1年）")
    ax.legend(frameon=False, fontsize=9, ncol=3, loc="upper center", bbox_to_anchor=(0.4, -0.17))
    ax.set_title("過去と予約の入り方が変わると、倍率・足し算の見込みは片寄る（7日前）")
    save(fig, "a1028_shift.png", SRC, y=-0.1)

    # 図3：1回分の3年目の60日（7日前の予約と見込み）
    t = one.iloc[150:210]
    fig, ax = plt.subplots(figsize=(8.4, 4.2))
    ax.plot(t.day_year3, t.final_people, color=INK, lw=1.6, label="当日の人数（本当）")
    ax.plot(t.day_year3, t.on_books_L7, color=GRAY, lw=1, label="7日前の予約の人数（①）")
    ax.plot(t.day_year3, t["fc_L7_②"], color=ORANGE, lw=1, ls="-", label="②倍率で見込んだ人数")
    ax.plot(t.day_year3, t["fc_L7_④"], color=BLUE, lw=1, ls="--", label="④予約を使わない見込み")
    ax.set_xlabel("3年目の何日目か（1回分の乱数）"); ax.set_ylabel("人")
    ax.legend(frameon=False, fontsize=9, ncol=2, loc="upper center", bbox_to_anchor=(0.5, -0.17))
    ax.set_title("7日前の予約は当日より少ないが、倍率を掛けると日ごとの上下をおおむね追える")
    save(fig, "a1028_series.png", SRC, y=-0.2)
    print(json.dumps(res, ensure_ascii=False, indent=1)); print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()

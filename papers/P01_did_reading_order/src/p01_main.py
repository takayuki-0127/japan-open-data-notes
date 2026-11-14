"""P01 差の差の新しい推定を、読む順番に試す。
1. シミュレーション（本当の効果が分かっている）：5つの場面で TWFE・Callaway–Sant'Anna・Sun–Abraham を500回ずつ比べる
2. Goodman-Bacon の分解と、処置された単位×時点の重み（負の重み）
3. 相対時点のダミーを途中で切った TWFE のイベントスタディが、効果の育ち方だけで「事前のずれ」を作る様子
4. Rambachan–Roth の考え方（相対的な大きさの制約）を簡略化した感度分析
5. 実データ：F296 の都道府県パネル（設計B、2024・2025年に処置が始まった9県）
使い方: cd src && python p01_main.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from did_tools import att_gt, bacon, cell_weights, cs_aggregate, sun_abraham, twfe_event_trimmed, twfe_static

ROOT = Path(__file__).resolve().parents[1]
DATA, RES = ROOT / "data", ROOT / "results"
RES.mkdir(exist_ok=True)
SEED = 20261114
R = lambda x, k=4: None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), k)

# ---------------------------------------------------------------- 1. シミュレーション
T = 20
COHORTS = [6, 11, 16]
N_PER = 10


def tau(scn, g, e):
    """場面ごとの本当の効果（処置後 e≥0 のみ）。"""
    if scn == "S1_一定":
        return 1.0
    if scn in ("S2_育つ", "S5_育つ_処置されない単位なし"):
        return 0.2 * (e + 1)
    if scn == "S3_組で違う":
        return {6: 1.5, 11: 1.0, 16: 0.5}[g] + 0.15 * e
    if scn == "S4_前提が崩れる":
        return 1.0
    raise ValueError(scn)


def simulate(scn, rng):
    gs = [g for g in COHORTS for _ in range(N_PER)]
    if scn != "S5_育つ_処置されない単位なし":
        gs += [np.inf] * N_PER
    rows = []
    for i, g in enumerate(gs):
        a = rng.normal(0, 1)
        for t in range(1, T + 1):
            e = t - g
            eff = tau(scn, g, e) if np.isfinite(g) and e >= 0 else 0.0
            drift = 0.04 * t if (scn == "S4_前提が崩れる" and np.isfinite(g)) else 0.0   # 処置される単位だけ少しずつ上向く
            rows.append({"unit": i, "t": t, "g": g, "tau": eff, "drift": drift})
    d = pd.DataFrame(rows)
    b = {t: 0.1 * t + np.sin(t / 3) for t in range(1, T + 1)}
    unit_fe = d.drop_duplicates("unit").assign(a=rng.normal(0, 1, len(gs))).set_index("unit")["a"]
    d["y"] = d.unit.map(unit_fe) + d.t.map(b) + d.tau + d.drift + rng.normal(0, 0.5, len(d))
    return d


def truth(d):
    tr = d[(d.t >= d.g)]
    return float(tr.tau.mean())


def estimate_all(d):
    tw, _, _ = twfe_static(d)
    ctrl = "notyet" if not np.isinf(d.g).any() else "never"
    a = att_gt(d, control=ctrl)
    cs, _ = cs_aggregate(a)
    out = {"truth": truth(d), "TWFE": tw, "CS": cs}
    if np.isinf(d.g).any():
        out["SA"], _ = sun_abraham(d)
    else:
        out["SA"] = np.nan          # Sun–Abraham は処置されない単位（または最後の組）を比較に使う。ここでは省く
    return out


SCN = ["S1_一定", "S2_育つ", "S3_組で違う", "S4_前提が崩れる", "S5_育つ_処置されない単位なし"]
REPS = 500
rng = np.random.default_rng(SEED)
rows = []
for scn in SCN:
    for r in range(REPS):
        d = simulate(scn, rng)
        e = estimate_all(d)
        rows.append({"scenario": scn, "rep": r, **e})
sim = pd.DataFrame(rows)
sim.to_csv(RES / "sim_reps.csv", index=False)
summ = []
for scn, g in sim.groupby("scenario", sort=False):
    for est in ["TWFE", "CS", "SA"]:
        err = g[est] - g.truth
        if err.isna().all():
            continue
        summ.append({"scenario": scn, "estimator": est, "truth_mean": R(g.truth.mean()), "est_mean": R(g[est].mean()),
                     "bias": R(err.mean()), "rmse": R(np.sqrt((err ** 2).mean())), "bias_pct": R(err.mean() / g.truth.mean() * 100, 1)})
summ = pd.DataFrame(summ)
summ.to_csv(RES / "sim_summary.csv", index=False)
print(summ)

# ---------------------------------------------------------------- 2. 1回分のデータで、TWFE の中身を見る（S2 と S5）
rng1 = np.random.default_rng(SEED + 1)
one = {s: simulate(s, rng1) for s in ["S2_育つ", "S5_育つ_処置されない単位なし", "S4_前提が崩れる"]}
one["S2_育つ"].to_csv(DATA / "sim_S2_one.csv", index=False)
bac = {}
for s in ["S2_育つ", "S5_育つ_処置されない単位なし"]:
    b = bacon(one[s])
    b["w_x_est"] = b.w * b.est
    b.to_csv(RES / f"bacon_{s}.csv", index=False)
    tw, _, _ = twfe_static(one[s])
    cw = cell_weights(one[s])
    bac[s] = {"twfe": R(tw), "bacon_weighted_sum": R(b.w_x_est.sum()), "bacon_weight_sum": R(b.w.sum()),
              "truth": R(truth(one[s])),
              "weight_late_vs_early": R(b.loc[b.kind == "遅い組 vs すでに処置された組", "w"].sum()),
              "est_late_vs_early_mean": R(np.average(b.loc[b.kind == "遅い組 vs すでに処置された組", "est"],
                                                    weights=b.loc[b.kind == "遅い組 vs すでに処置された組", "w"])),
              "n_treated_cells": int(len(cw)), "n_negative_cells": int((cw.w < 0).sum()),
              "sum_negative_weights": R(cw.loc[cw.w < 0, "w"].sum()),
              "negative_cells_e_min": int((cw.loc[cw.w < 0, "t"] - cw.loc[cw.w < 0, "g"]).min()) if (cw.w < 0).any() else None}
    cw.assign(e=cw.t - cw.g)[["unit", "g", "t", "e", "tau", "w"]].groupby(["g", "e"]).agg(w=("w", "sum"), tau=("tau", "mean")).reset_index() \
        .to_csv(RES / f"cell_weights_{s}.csv", index=False)

# ---------------------------------------------------------------- 3. イベントスタディ（S2・1回分）
d = one["S2_育つ"]
tr_ev = twfe_event_trimmed(d, lo=-5, hi=5)
_, sa_ev = sun_abraham(d)
_, cs_ev = cs_aggregate(att_gt(d, control="never"))
true_ev = pd.Series({e: (0.2 * (e + 1) if e >= 0 else 0.0) for e in range(-10, 15)})
ev = pd.DataFrame({"twfe_trimmed": tr_ev, "sun_abraham": sa_ev, "cs_varying_base": cs_ev, "truth": true_ev})
ev.index.name = "e"
ev = ev.loc[-8:12]
ev.round(4).to_csv(RES / "event_study_S2.csv")

# イベントスタディの事前の係数を500回で見る（S2）：途中で切った TWFE は事前に効果があるように見えるか
rng2 = np.random.default_rng(SEED + 2)
pre = []
for r in range(200):
    dd = simulate("S2_育つ", rng2)
    tr_e = twfe_event_trimmed(dd, lo=-5, hi=5)
    _, sa_e = sun_abraham(dd)
    pre.append({"rep": r, "twfe_pre_mean": tr_e.loc[[-5, -4, -3, -2]].mean(), "sa_pre_mean": sa_e.loc[[-5, -4, -3, -2]].mean(),
                "twfe_e5": tr_e.loc[5], "sa_e5": sa_e.loc[5]})
pre = pd.DataFrame(pre)
pre.to_csv(RES / "event_pre_reps_S2.csv", index=False)

# ---------------------------------------------------------------- 4. Rambachan–Roth（簡略版）


def rr_relative(ev_series, boot_e0, Mbars):
    """相対的な大きさの制約（簡略版）：処置直後（e=0）の偏りは、事前の1期ごとの動きの最大 m の M̄ 倍まで。
    区間 = [β0 − M̄m − 1.96·se, β0 + M̄m + 1.96·se]。元の論文の最適な区間ではなく、偏りの上限を足しただけ。"""
    pre_e = [e for e in ev_series.index if e < 0]
    m = float(np.max(np.abs(ev_series.loc[pre_e])))
    b0 = float(ev_series.loc[0])
    se = float(np.std(boot_e0, ddof=1))
    rows = [{"Mbar": M, "lo": b0 - M * m - 1.96 * se, "hi": b0 + M * m + 1.96 * se} for M in Mbars]
    tab = pd.DataFrame(rows)
    covers0 = tab[(tab.lo <= 0) & (tab.hi >= 0)]
    breakdown = float(covers0.Mbar.min()) if len(covers0) else None
    return tab, {"beta_e0": b0, "se_e0": se, "max_pre_step": m, "breakdown_Mbar": breakdown}


def boot_cs_e0(df, control, B, seed):
    rng_b = np.random.default_rng(seed)
    units = df.unit.unique()
    vals = []
    for _ in range(B):
        pick = rng_b.choice(units, len(units), replace=True)
        bd = pd.concat([df[df.unit == u].assign(unit=k) for k, u in enumerate(pick)], ignore_index=True)
        if not np.isinf(bd.g).any() and control == "never":
            continue
        if not np.isfinite(bd.g).any():
            continue
        a = att_gt(bd, control=control)
        _, e_ = cs_aggregate(a)
        if 0 in e_.index:
            vals.append(float(e_.loc[0]))
    return np.array(vals)


MB = np.round(np.arange(0, 2.01, 0.05), 2)
d4 = one["S4_前提が崩れる"]
_, ev4 = cs_aggregate(att_gt(d4, control="never"))
rr4_tab, rr4 = rr_relative(ev4, boot_cs_e0(d4, "never", 299, SEED + 3), MB)
rr4["truth_e0"] = 1.0
rr4_tab.round(4).to_csv(RES / "rr_S4.csv", index=False)

# ---------------------------------------------------------------- 5. 実データ（F296 の設計B）
p = pd.read_csv(DATA / "panel_f296.csv")
Y0, Y1 = 2015, 2025
B = p[p.year.between(Y0, Y1)].copy()
B["g"] = np.where(B["g"] <= Y1, B["g"], np.inf)
real = B.rename(columns={"code": "unit", "year": "t"})[["unit", "t", "g", "emp_rate", "pref"]].rename(columns={"emp_rate": "y"})
tw_r, _, _ = twfe_static(real)
a_r = att_gt(real, control="never")
cs_r, ev_r = cs_aggregate(a_r)
sa_r, sa_ev_r = sun_abraham(real)
bac_r = bacon(real)
bac_r["w_x_est"] = bac_r.w * bac_r.est
bac_r.to_csv(RES / "bacon_real.csv", index=False)
cw_r = cell_weights(real)
boot_r = boot_cs_e0(real, "never", 499, SEED + 4)
rr_r_tab, rr_r = rr_relative(ev_r, boot_r, MB)
rr_r_tab.round(4).to_csv(RES / "rr_real.csv", index=False)
pd.DataFrame({"cs_event": ev_r, "sa_event": sa_ev_r}).round(4).to_csv(RES / "event_study_real.csv")
n_by = real.drop_duplicates("unit").groupby("g").size()

main = {
    "sim": {"design": {"T": T, "cohorts": COHORTS, "units_per_group": N_PER, "reps": REPS, "noise_sd": 0.5},
            "summary": summ.to_dict(orient="records"), "bacon_one_draw": bac,
            "event_pre_S2": {"twfe_trimmed_pre_mean": R(pre.twfe_pre_mean.mean()), "sa_pre_mean": R(pre.sa_pre_mean.mean()),
                             "twfe_trimmed_e5_mean": R(pre.twfe_e5.mean()), "sa_e5_mean": R(pre.sa_e5.mean()), "truth_e5": 1.2},
            "rr_S4": {k: R(v) for k, v in rr4.items()}},
    "real": {"years": [Y0, Y1], "outcome": "就業率（%pt）", "cohorts": {("なし" if np.isinf(k) else str(int(k))): int(v) for k, v in n_by.items()},
             "twfe": R(tw_r), "cs_never": R(cs_r), "sun_abraham": R(sa_r),
             "cs_pre_e_minus1": R(ev_r.get(-1)), "bacon_weight_late_vs_early": R(bac_r.loc[bac_r.kind == "遅い組 vs すでに処置された組", "w"].sum()),
             "bacon_weight_treated_vs_never": R(bac_r.loc[bac_r.kind == "処置 vs 処置されない", "w"].sum()),
             "n_negative_cells": int((cw_r.w < 0).sum()), "n_treated_cells": int(len(cw_r)),
             "rr": {k: R(v) for k, v in rr_r.items()}},
}
json.dump(main, open(RES / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(json.dumps(main["real"], ensure_ascii=False, indent=1))
print(json.dumps(main["sim"]["bacon_one_draw"], ensure_ascii=False, indent=1))
print(main["sim"]["event_pre_S2"], main["sim"]["rr_S4"])

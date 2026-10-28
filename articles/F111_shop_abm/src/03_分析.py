"""03 分析：実データの「店の減り方」と、エージェントベースのモデル（ABM）の照合・2050年への投影。

実行： OMP_NUM_THREADS=1 nice -n 10 python3 src/03_分析.py
乱数の種：町ごとに (種の基準 + 町の番号)。基準は 42。
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from abm import BASE, pop_path_loglinear, simulate, variant  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
SEED = 42
t0 = time.time()


def log(*a):
    print(f"[{time.time() - t0:6.0f}s]", *a, flush=True)


# ---------------------------------------------------------------- 実データ
d = pd.read_csv(ROOT / "data" / "panel.csv", dtype={"code": str, "pref": str})
d["p2012"] = d.pop2010 * (d.pop2015 / d.pop2010) ** 0.4
d["p2016"] = d.pop2015 * (d.pop2020 / d.pop2015) ** 0.2
d["p2021"] = d.pop2020 * (d.pop2020 / d.pop2015) ** 0.2
d = d[(d.stores2012 > 0) & (d.stores2021 > 0) & d.p2012.notna() & d.habitable_km2.notna()].copy()
d["ds"] = np.log(d.stores2021 / d.stores2012)
d["dp"] = np.log(d.p2021 / d.p2012)
d["size_q"] = pd.qcut(np.log(d.p2012), 5, labels=False)
log("towns", len(d))

out = {}


def ols(formula, data):
    m = smf.ols(formula, data).fit(cov_type="HC1")
    return m


real = {}
m = ols("ds ~ dp", d)
real["beta_all"] = [m.params.dp, m.bse.dp, m.params.Intercept]
m = ols("ds ~ dp + C(pref)", d)
real["beta_prefFE"] = [m.params.dp, m.bse.dp]
# 2016→2021（同じ経済センサス-活動調査どうし）
dd = d[d.stores2016 > 0].copy()
dd["ds2"] = np.log(dd.stores2021 / dd.stores2016)
dd["dp2"] = np.log(dd.p2021 / dd.p2016)
m = ols("ds2 ~ dp2", dd)
real["beta_2016_2021"] = [m.params.dp2, m.bse.dp2, m.params.Intercept]
# 2002→2007（商業統計どうし。人口は 2005→2010 の伸びで代用）
de = d[(d.stores2002 > 0) & (d.stores2007 > 0) & d.pop2005.notna()].copy()
de["ds3"] = np.log(de.stores2007 / de.stores2002)
de["dp3"] = np.log(de.pop2010 / de.pop2005)
m = ols("ds3 ~ dp3", de)
real["beta_2002_2007_proxy"] = [m.params.dp3, m.bse.dp3, m.params.Intercept]
# 従業者
d["dw"] = np.log(d.workers2021 / d.workers2012)
m = ols("dw ~ dp", d[np.isfinite(d.dw)])
real["beta_workers"] = [m.params.dp, m.bse.dp, m.params.Intercept]
# 断面：店の数 ∝ 人口^b
m = ols("np.log(stores2021) ~ np.log(p2021)", d)
real["xsec_b"] = [m.params.iloc[1], m.bse.iloc[1]]
by = []
for q, g in d.groupby("size_q"):
    mm = smf.ols("ds ~ dp", g).fit()
    by.append({"size_q": int(q), "pop_median": float(g.p2012.median()), "n": len(g),
               "beta": mm.params.dp, "ds_mean": g.ds.mean(), "dp_mean": g.dp.mean(),
               "per1000_2012": float((g.stores2012 / g.p2012 * 1000).median()),
               "per1000_2021": float((g.stores2021 / g.p2021 * 1000).median())})
real["by_size"] = by
# 人口の減り方で5つに分けた店の減り方（非線形か）
d["dp_q"] = pd.qcut(d.dp, 5, labels=False)
real["by_decline"] = d.groupby("dp_q").agg(dp=("dp", "mean"), ds=("ds", "mean"), n=("ds", "size")).reset_index().to_dict("records")
out["real"] = real
log("real", {k: np.round(v, 3).tolist() for k, v in real.items() if k.startswith("beta") or k == "xsec_b"})


# ---------------------------------------------------------------- ABM：2012→2021
def run_all(params, towns, years, p_from, p_to, seed_base=SEED, access=False):
    rows = []
    for i, r in enumerate(towns.itertuples()):
        rng = np.random.default_rng(seed_base + i)
        path = pop_path_loglinear(getattr(r, p_from), getattr(r, p_to), years)
        res = simulate(path, r.habitable_km2, r.stores2012 if p_from == "p2012" else r.s0, params, rng,
                       record_access=access)
        row = {"code": r.code, "n0": res["n"][0], "n1": res["n"][-1], "leak0": res["leak"][0], "leak1": res["leak"][-1]}
        if access:
            row.update({"acc1_0": res["acc1"][0], "acc1_1": res["acc1"][-1],
                        "acc2_0": res["acc2"][0], "acc2_1": res["acc2"][-1]})
        rows.append(row)
    return pd.DataFrame(rows)


def compare(sim, towns):
    x = towns[["code", "ds", "dp", "size_q"]].merge(sim, on="code")
    x["ds_abm"] = np.log(np.maximum(x.n1, 0.5) / x.n0)
    mm = smf.ols("ds_abm ~ dp", x).fit()
    byq = [smf.ols("ds_abm ~ dp", g).fit().params.dp for _, g in x.groupby("size_q")]
    return x, {"beta": mm.params.dp, "icpt": mm.params.Intercept, "mean_ds": x.ds_abm.mean(),
               "beta_by_size": byq}


# 校正：出店候補の多さ（倍率）を、町ごとの店の変化の平均が実データ（2012→2021）に合うように選ぶ。
# 町の外への重みの伸びは基準では 0（通販などの伸びは前提を変える確認で入れる）
calib = []
for m_ in [0.75, 1.0, 1.25, 1.5, 2.0]:
    sim = run_all(variant(entry_mult=m_), d, 9, "p2012", "p2021")
    x, s = compare(sim, d)
    calib.append({"entry_mult": m_, **{k: v for k, v in s.items() if k != "beta_by_size"}})
    log("calib m", m_, round(s["mean_ds"], 4), "real", round(d.ds.mean(), 4), "beta", round(s["beta"], 3))
calib = pd.DataFrame(calib)
cs = calib.sort_values("entry_mult")
target = d.ds.mean()
if cs.mean_ds.is_monotonic_increasing and cs.mean_ds.min() <= target <= cs.mean_ds.max():
    m_best = float(np.interp(target, cs.mean_ds.values, cs.entry_mult.values))  # 2点の間を直線でつなぐ
else:
    m_best = float(cs.iloc[(cs.mean_ds - target).abs().argmin()].entry_mult)
out["calibration"] = calib.to_dict("records")
out["entry_mult_best"] = m_best
g_best = 0.0
P = variant(entry_mult=m_best)
log("best entry_mult", m_best)

# 照合（種を変えて5回）
val = []
xs = []
for k in range(3):
    sim = run_all(P, d, 9, "p2012", "p2021", seed_base=SEED + 1000 * k)
    x, s = compare(sim, d)
    val.append(s)
    xs.append(x.assign(rep=k))
xall = pd.concat(xs)
xall.to_csv(RES / "abm_2012_2021_by_town.csv", index=False)
x0 = xs[0]
# 町ごとの予測の当たり方：ABM と「人口に比例」と「変化なし（全国の平均だけ）」
x0["ds_prop"] = x0.dp + (d.ds.mean() - d.dp.mean())
x0["ds_flat"] = d.ds.mean()
rmse = {k: float(np.sqrt(((x0.ds - x0[k]) ** 2).mean())) for k in ["ds_abm", "ds_prop", "ds_flat"]}
out["validation"] = {"runs": val, "rmse": rmse,
                     "beta_mean": float(np.mean([v["beta"] for v in val])),
                     "beta_range": [float(min(v["beta"] for v in val)), float(max(v["beta"] for v in val))],
                     "beta_by_size_mean": np.mean([v["beta_by_size"] for v in val], 0).tolist()}
log("validation", out["validation"]["beta_mean"], rmse)

# ---------------------------------------------------------------- 2020→2050 への投影
pj = d[d.ipss2050.notna()].copy()
pj["s0"] = pj.stores2021
pj["p2020"] = pj.pop2020
pj["p2050"] = pj.ipss2050
pj["dp50"] = np.log(pj.p2050 / pj.p2020)


def project(params, towns, seed_base=SEED + 7):
    sim = run_all(params, towns, 30, "p2020", "p2050", seed_base=seed_base, access=True)
    x = towns[["code", "p2020", "p2050", "dp50", "size_q", "s0"]].merge(sim, on="code")
    x["ds50"] = np.log(np.maximum(x.n1, 0.5) / x.n0)
    return x


proj = project(P, pj)
proj.to_csv(RES / "abm_2020_2050_by_town.csv", index=False)


def summarize(x):
    r = {"beta": float(smf.ols("ds50 ~ dp50", x).fit().params.dp50),
         "ds50_mean": float(x.ds50.mean()), "dp50_mean": float(x.dp50.mean()),
         "acc1_0": float(np.average(x.acc1_0, weights=x.p2020)), "acc1_1": float(np.average(x.acc1_1, weights=x.p2050)),
         "acc2_0": float(np.average(x.acc2_0, weights=x.p2020)), "acc2_1": float(np.average(x.acc2_1, weights=x.p2050)),
         "towns_le3": int((x.n1 <= 3).sum()), "towns_le3_now": int((x.n0 <= 3).sum()),
         "towns_zero": int((x.n1 == 0).sum())}
    byq = []
    for q, g in x.groupby("size_q"):
        byq.append({"size_q": int(q), "n": len(g), "dp50": float(g.dp50.mean()), "ds50": float(g.ds50.mean()),
                    "acc1_0": float(np.average(g.acc1_0, weights=g.p2020)), "acc1_1": float(np.average(g.acc1_1, weights=g.p2050)),
                    "acc2_0": float(np.average(g.acc2_0, weights=g.p2020)), "acc2_1": float(np.average(g.acc2_1, weights=g.p2050)),
                    "leak0": float(g.leak0.mean()), "leak1": float(g.leak1.mean())})
    r["by_size"] = byq
    return r


out["projection_base"] = summarize(proj)
log("projection", {k: v for k, v in out["projection_base"].items() if k != "by_size"})

# ---------------------------------------------------------------- 前提を変える（投影）
# 計算を抑えるため、規模の5区分から各80町（計400町）を選んで行う
rng = np.random.default_rng(SEED)
sub = pd.concat([g.sample(min(80, len(g)), random_state=SEED) for _, g in pj.groupby("size_q")])
scen = {
    "基準": P,
    "距離の減り方 λ=0.75km": variant(entry_mult=m_best, g_out=g_best, lam=0.75),
    "距離の減り方 λ=3km": variant(entry_mult=m_best, g_out=g_best, lam=3.0),
    "余裕が小さい（固定費÷売上 0.8〜1）": variant(entry_mult=m_best, g_out=g_best, margin_lo=0.8),
    "余裕が大きい（0.4〜1）": variant(entry_mult=m_best, g_out=g_best, margin_lo=0.4),
    "赤字1年で閉店": variant(entry_mult=m_best, g_out=g_best, k_exit=1),
    "赤字3年で閉店": variant(entry_mult=m_best, g_out=g_best, k_exit=3),
    "入れ替わり 年1%": variant(entry_mult=m_best, g_out=g_best, q_churn=0.01),
    "入れ替わり 年4%": variant(entry_mult=m_best, g_out=g_best, q_churn=0.04),
    "町の外の伸び +1%/年": variant(entry_mult=m_best, g_out=g_best + 0.01),
    "町の外の伸び +2%/年": variant(entry_mult=m_best, g_out=g_best + 0.02),
    "人口減は周辺ほど速い": variant(entry_mult=m_best, g_out=g_best, periphery=1.0),
    "人口が中心に集まる（ρ=0.15）": variant(entry_mult=m_best, g_out=g_best, rho=0.15),
    "人口が散らばる（ρ=0.5）": variant(entry_mult=m_best, g_out=g_best, rho=0.5),
}
srows = []
for name, prm in scen.items():
    for k in range(2):
        x = project(prm, sub, seed_base=SEED + 50 + 1000 * k)
        s = summarize(x)
        q0 = s["by_size"][0]
        srows.append({"scenario": name, "rep": k, "beta": s["beta"], "ds50": s["ds50_mean"],
                      "acc1_0": s["acc1_0"], "acc1_1": s["acc1_1"], "acc2_0": s["acc2_0"], "acc2_1": s["acc2_1"],
                      "small_ds50": q0["ds50"], "small_dp50": q0["dp50"],
                      "small_acc1_1": q0["acc1_1"], "small_acc1_0": q0["acc1_0"],
                      "small_acc2_1": q0["acc2_1"], "small_acc2_0": q0["acc2_0"]})
    log("scenario", name, round(srows[-1]["beta"], 3), round(srows[-1]["small_ds50"], 3))
sc = pd.DataFrame(srows)
sc.to_csv(RES / "scenarios_projection.csv", index=False)
out["scenarios"] = sc.groupby("scenario", sort=False).mean(numeric_only=True).drop(columns="rep").reset_index().to_dict("records")

# 各シナリオで 2012→2021 の照合もやり直す（前提を変えても実データに合うか）
vrows = []
for name, prm in scen.items():
    if name == "基準":
        continue
    sim = run_all(prm, sub.assign(stores2012=sub.stores2012), 9, "p2012", "p2021", seed_base=SEED + 300)
    x, s = compare(sim, sub)
    vrows.append({"scenario": name, "beta_2012_2021": s["beta"], "mean_ds": s["mean_ds"]})
x, s = compare(run_all(P, sub, 9, "p2012", "p2021", seed_base=SEED + 300), sub)
vrows.insert(0, {"scenario": "基準", "beta_2012_2021": s["beta"], "mean_ds": s["mean_ds"]})
out["scenario_validation"] = vrows
out["sub_real_mean_ds"] = float(sub.ds.mean())
log("scenario validation done")

# ---------------------------------------------------------------- 1つの架空の町で長く見る（転換点はあるか）
long_rows = []
for pop0, st0, area in [(1000, 12, 20), (3000, 30, 40), (10000, 85, 60)]:
    for name, prm in [("基準", P), ("余裕が小さい", variant(entry_mult=m_best, g_out=g_best, margin_lo=0.8)),
                      ("町の外の伸び +2%/年", variant(entry_mult=m_best, g_out=g_best + 0.02)),
                      ("赤字1年で閉店", variant(entry_mult=m_best, g_out=g_best, k_exit=1))]:
        for k in range(20):
            path = pop_path_loglinear(pop0, pop0 * 0.3, 50)
            r = simulate(path, area, st0, prm, np.random.default_rng(SEED + 9000 + k), record_access=True)
            for t in range(51):
                long_rows.append({"pop0": pop0, "scenario": name, "rep": k, "year": t, "pop": path[t],
                                  "n": r["n"][t], "acc1": r["acc1"][t], "acc2": r["acc2"][t], "leak": r["leak"][t]})
lg = pd.DataFrame(long_rows)
lg.to_csv(RES / "synthetic_long.csv", index=False)
summ = lg.groupby(["pop0", "scenario", "year"]).agg(n=("n", "mean"), n_lo=("n", lambda v: np.percentile(v, 10)),
                                                    n_hi=("n", lambda v: np.percentile(v, 90)), pop=("pop", "mean"),
                                                    acc1=("acc1", "mean"), acc2=("acc2", "mean"), leak=("leak", "mean")).reset_index()
summ.to_csv(RES / "synthetic_long_summary.csv", index=False)
# 最後の店が消える年（20回のうち何回消えたか）
zero = lg[lg.n == 0].groupby(["pop0", "scenario", "rep"]).year.min().reset_index()
out["synthetic_zero"] = zero.groupby(["pop0", "scenario"]).year.agg(["count", "median"]).reset_index().to_dict("records")
log("synthetic done")

out["elapsed_s"] = time.time() - t0
json.dump(out, open(RES / "results.json", "w"), ensure_ascii=False, indent=1, default=float)
log("saved")

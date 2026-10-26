"""境界不連続デザイン：県境をはさんで接する市区町村ペアの中で比べる。

主な式（ペアの中の差＝ペア固定効果と同じ）：
  (Δlog 従業者_a − Δlog 従業者_b) = β (Δlog 最低賃金_a − Δlog 最低賃金_b) + 誤差
  Δ は 2016→2021年。定数項なし（ペアの向きに意味がないため）。
  標準誤差は「県の組（境界）」でクラスタ。
"""
import json

import numpy as np
import pandas as pd
import statsmodels.api as sm

from common import DATA, RES, SEED

RES.mkdir(exist_ok=True)
m = pd.read_csv(DATA / "muni.csv").set_index("code")
P = pd.read_csv(DATA / "pairs.csv")
P["pa"], P["pb"] = P.code_a // 1000, P.code_b // 1000
P["seg"] = P.pa.astype(str) + "-" + P.pb.astype(str)
METRO = [{11, 12, 13, 14}, {26, 27, 28, 29}, {21, 23, 24}]
P["metro"] = [any(a in s and b in s for s in METRO) for a, b in zip(P.pa, P.pb)]


def build(pairs, ycol, xcol="dlog_mw"):
    a, b = m.loc[pairs.code_a], m.loc[pairs.code_b]
    d = pd.DataFrame({
        "dy": a[ycol].values - b[ycol].values,
        "dx": a[xcol].values - b[xcol].values,
        "seg": pairs.seg.values,
        "w": np.sqrt(a["pop_21"].values * b["pop_21"].values),
        "mwgap": np.abs(a["mw20"].values - b["mw20"].values),
    }).replace([np.inf, -np.inf], np.nan).dropna()
    return d


def fit(d, weight=False, winsor=0.01):
    d = d.copy()
    if winsor:
        lo, hi = d.dy.quantile([winsor, 1 - winsor])
        d["dy"] = d.dy.clip(lo, hi)
    mod = sm.WLS(d.dy, d[["dx"]], weights=d.w if weight else np.ones(len(d)))
    r = mod.fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(d.seg)[0]})
    b, se = r.params["dx"], r.bse["dx"]
    return {"beta": b, "se": se, "lo": b - 1.96 * se, "hi": b + 1.96 * se,
            "p": r.pvalues["dx"], "n_pairs": len(d), "n_seg": d.seg.nunique()}


touch = P[P.kind == "touch"]
res = {}
for ind in ["food", "retail", "life", "manuf", "medical", "total"]:
    res[f"main_{ind}"] = fit(build(touch, f"dlog_{ind}"))
# 三重差：飲食 − 製造
m["dlog_food_minus_manuf"] = m.dlog_food - m.dlog_manuf
m["dlog_fr"] = np.log((m.emp_food_21 + m.emp_retail_21) / (m.emp_food_16 + m.emp_retail_16))
m["dlog_fr_minus_manuf"] = m.dlog_fr - m.dlog_manuf
res["main_food_minus_manuf"] = fit(build(touch, "dlog_food_minus_manuf"))
res["main_foodretail"] = fit(build(touch, "dlog_fr"))
res["main_fr_minus_manuf"] = fit(build(touch, "dlog_fr_minus_manuf"))

# 頑健性（飲食＋小売 を主に）
rob = {}
Y = "dlog_fr"
rob["基本（接するペア）"] = res["main_foodretail"]
rob["中心が20km以内のペアも入れる"] = fit(build(P[(P.kind == "touch") | (P.dist_km <= 20)], Y))
rob["大都市の境を除く"] = fit(build(touch[~touch.metro], Y))
rob["人口で重みづけ"] = fit(build(touch, Y), weight=True)
d0 = build(touch, Y)
rob["最低賃金の差が大きいペアだけ（20円以上）"] = fit(d0[d0.mwgap >= 20])
rob["外れ値を丸めない"] = fit(d0, winsor=0)
rob["事業所数で見る（飲食）"] = fit(build(touch, "dlog_est_food"))
rob["製造業を引く（三重差）"] = res["main_fr_minus_manuf"]

# 水準の比較（2021年）：ペアの中で、最低賃金が高い側は人口あたり飲食・小売の従業者が少ないか
m["lv_fr"] = np.log((m.emp_food_21 + m.emp_retail_21) / m.pop_21)
m["lmw20"] = np.log(m.mw20)
m["lv_manuf"] = np.log(m.emp_manuf_21 / m.pop_21)
lev = {"飲食＋小売（人口あたり、2021）": fit(build(touch, "lv_fr", "lmw20")),
       "製造業（人口あたり、2021）": fit(build(touch, "lv_manuf", "lmw20"))}

# 並べ替え（境界ごとに最低賃金の差の符号をランダムに入れ替える）
rng = np.random.default_rng(SEED)
d = build(touch, Y)
lo, hi = d.dy.quantile([0.01, 0.99]); d["dy"] = d.dy.clip(lo, hi)
obs = (d.dx * d.dy).sum() / (d.dx ** 2).sum()
segs = d.seg.unique()
perm = []
for _ in range(2000):
    sgn = dict(zip(segs, rng.choice([-1, 1], len(segs))))
    s = d.seg.map(sgn)
    perm.append(((d.dx * s) * d.dy).sum() / (d.dx ** 2).sum())
perm = np.array(perm)
p_perm = float((np.abs(perm) >= abs(obs)).mean())

desc = {
    "pairs_touch": int((P.kind == "touch").sum()),
    "pairs_near20_extra": int((P.kind == "near20").sum()),
    "segments": int(touch.seg.nunique()),
    "munis_on_border": int(len(set(touch.code_a) | set(touch.code_b))),
    "dx_sd": float(d0.dx.std()), "dx_absmax": float(d0.dx.abs().max()),
    "mwgap_yen_median": float(d0.mwgap.median()), "mwgap_yen_max": float(d0.mwgap.max()),
    "dlog_mw_range": [float(m.dlog_mw.min()), float(m.dlog_mw.max())],
    "perm_p": p_perm, "obs_beta_fr": float(obs),
    "mean_dlog": {k: float(m[f"dlog_{k}"].replace([np.inf, -np.inf], np.nan).median()) for k in ["food", "retail", "manuf", "total"]},
}
json.dump({"main": res, "robust": rob, "level": lev, "desc": desc}, open(RES / "estimates.json", "w"),
          ensure_ascii=False, indent=1, default=float)
tab = pd.DataFrame(res).T[["beta", "lo", "hi", "p", "n_pairs", "n_seg"]].round(3)
tab.to_csv(RES / "main_by_industry.csv")
rt = pd.DataFrame(rob).T[["beta", "lo", "hi", "p", "n_pairs", "n_seg"]].round(3)
rt.to_csv(RES / "robustness.csv")
pd.DataFrame(lev).T[["beta", "lo", "hi", "p", "n_pairs"]].round(3).to_csv(RES / "level_2021.csv")
print(tab.to_string()); print(rt.to_string()); print(pd.DataFrame(lev).T.round(3).to_string()); print(json.dumps(desc, ensure_ascii=False, indent=1))

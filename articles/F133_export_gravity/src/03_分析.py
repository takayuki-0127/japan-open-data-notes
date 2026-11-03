"""03 分析：重力モデル（PPML）の推定と頑健性。results/ に書き出す。"""
import os, json, warnings
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

warnings.filterwarnings("ignore")
np.random.seed(133)
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
R = os.path.join(ROOT, "results"); os.makedirs(R, exist_ok=True)
pan = pd.read_csv(os.path.join(ROOT, "data", "panel.csv"))
pan["x"] = pan.exports_usd / 1e9          # 十億ドル
pan["lgdp"] = np.log(pan.gdp_imf_bn)
pan["lgdp_wb"] = np.log(pan.gdp_wb_bn)
pan["ldist"] = np.log(pan.dist_km)
pan["lgdppc"] = np.log(pan.gdp_imf_bn * 1e9 / pan["pop"])
T = pan[pan.cmd == "TOTAL"].dropna(subset=["lgdp", "ldist"]).copy()

def ppml(df, f, cl="iso3"):
    d = df.dropna(subset=[v for v in ["lgdp", "ldist", "lgdp_wb", "lgdppc"] if v in f]).copy()
    m = smf.glm("x ~ " + f, data=d, family=sm.families.Poisson()).fit(
        cov_type="cluster", cov_kwds={"groups": pd.factorize(d[cl])[0]}, maxiter=200)
    return m, d

def coef(m, v):
    if v not in m.params: return None
    b, s = m.params[v], m.bse[v]
    return {"b": round(float(b), 4), "lo": round(float(b - 1.96 * s), 4), "hi": round(float(b + 1.96 * s), 4)}

def fit_stats(m, d):
    yhat = m.fittedvalues; y = d.x
    r2_level = np.corrcoef(y, yhat)[0, 1] ** 2
    pos = y > 0
    r2_log = np.corrcoef(np.log(y[pos]), np.log(yhat[pos]))[0, 1] ** 2
    return round(float(r2_level), 3), round(float(r2_log), 3)

out = {}
BASE = "lgdp + ldist + landlocked + epa + C(year)"
m1, d1 = ppml(T, BASE)
out["n_countries"] = int(T.iso3.nunique()); out["n_obs"] = int(len(d1)); out["share_zero"] = round(float((d1.x == 0).mean()), 3)
out["M1_pooled"] = {v: coef(m1, v) for v in ["lgdp", "ldist", "landlocked", "epa"]}
out["M1_pooled"]["r2_level"], out["M1_pooled"]["r2_log_pos"] = fit_stats(m1, d1)

# GDP だけ・距離だけ・両方での説明力（2024年の断面ではなく全期間）
for nm, f in [("gdp_only", "lgdp + C(year)"), ("dist_only", "ldist + C(year)"), ("gdp_dist", "lgdp + ldist + C(year)")]:
    m, d = ppml(T, f); out["fit_" + nm] = dict(zip(["r2_level", "r2_log_pos"], fit_stats(m, d)))

# 地域の固定効果を加える
m1r, d1r = ppml(T, BASE + " + C(region)")
out["M1_region"] = {v: coef(m1r, v) for v in ["lgdp", "ldist", "epa"]}
out["M1_region"]["r2_level"], out["M1_region"]["r2_log_pos"] = fit_stats(m1r, d1r)

# 国と年の固定効果（距離は国の固定効果に吸収される）
Tfe = T[T.groupby("iso3").x.transform("sum") > 0]
m3, d3 = ppml(Tfe, "lgdp + epa + C(iso3) + C(year)")
out["M3_countryFE"] = {v: coef(m3, v) for v in ["lgdp", "epa"]}
m3b, _ = ppml(Tfe[Tfe.iso3 != "USA"], "lgdp + epa + C(iso3) + C(year)")
out["M3_countryFE_exUSA"] = {v: coef(m3b, v) for v in ["lgdp", "epa"]}

# 年ごとの距離の弾力性（断面の PPML、年の固定効果なし）
yr = []
for y, g in T.groupby("year"):
    m, d = ppml(g, "lgdp + ldist + landlocked" + (" + epa" if g.epa.nunique() > 1 else ""))
    c = coef(m, "ldist"); c2 = coef(m, "lgdp")
    yr.append({"year": int(y), "dist_b": c["b"], "dist_lo": c["lo"], "dist_hi": c["hi"],
               "gdp_b": c2["b"], "gdp_lo": c2["lo"], "gdp_hi": c2["hi"]})
pd.DataFrame(yr).to_csv(os.path.join(R, "by_year.csv"), index=False)

# 品目別（HS 2桁の章）
NAMES = {"TOTAL": "総額", "87": "自動車・部品（87類）", "84": "機械（84類）", "85": "電気機器（85類）", "90": "光学・精密機器（90類）",
         "72": "鉄鋼（72類）", "39": "プラスチック（39類）", "29": "有機化学品（29類）", "27": "鉱物性燃料（27類）"}
cm = []
for c, g in pan.groupby("cmd"):
    g = g.dropna(subset=["lgdp", "ldist"])
    m, d = ppml(g, BASE)
    r = {"cmd": c, "name": NAMES.get(c, c), "years": f"{int(g.year.min())}-{int(g.year.max())}", "n": int(len(d)),
         "share_zero": round(float((d.x == 0).mean()), 3)}
    for v in ["lgdp", "ldist", "epa"]:
        cc = coef(m, v); r.update({v: cc["b"], v + "_lo": cc["lo"], v + "_hi": cc["hi"]})
    r["r2_level"], r["r2_log_pos"] = fit_stats(m, d)
    cm.append(r)
pd.DataFrame(cm).to_csv(os.path.join(R, "by_commodity.csv"), index=False)

# 実績 ÷ 予測（M1、2015〜2024年の合計、輸出額の上位25か国）
d1 = d1.assign(pred=m1.fittedvalues)
rr = d1[d1.year >= 2015].groupby(["iso3", "wb_name"], as_index=False)[["x", "pred"]].sum()
rr["ratio"] = rr.x / rr.pred
rr = rr.sort_values("x", ascending=False)
rr.head(25).to_csv(os.path.join(R, "actual_vs_pred_top25.csv"), index=False)
out["top_share_2024"] = round(float(T[T.year == 2024].x.nlargest(10).sum() / T[T.year == 2024].x.sum()), 3)

# 頑健性（距離と GDP の係数）
rob = []
def add(name, m, extra=""):
    rob.append({"name": name, **{f"{v}_{k}": (coef(m, v) or {}).get(k) for v in ["ldist", "lgdp"] for k in ["b", "lo", "hi"]}, "note": extra})
add("基本：PPML（ゼロを含む、2000〜2024年）", m1)
m, _ = ppml(T[T.x > 0], BASE); add("PPML（ゼロを除く）", m)
d = T[T.x > 0].copy(); d["ly"] = np.log(d.x)
mo = smf.ols("ly ~ " + BASE, data=d).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(d.iso3)[0]})
rob.append({"name": "対数の OLS（ゼロを除く）", **{f"{v}_{k}": coef(mo, v)[k] for v in ["ldist", "lgdp"] for k in ["b", "lo", "hi"]}, "note": ""})
d = T.copy(); d["ly"] = np.log1p(d.x * 1000)   # 百万ドル単位で +1
mo2 = smf.ols("ly ~ " + BASE, data=d).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(d.iso3)[0]})
rob.append({"name": "対数の OLS（ln(1+百万ドル)、ゼロを含む）", **{f"{v}_{k}": coef(mo2, v)[k] for v in ["ldist", "lgdp"] for k in ["b", "lo", "hi"]}, "note": ""})
for a, b in [(2000, 2009), (2010, 2019), (2020, 2024)]:
    m, _ = ppml(T[(T.year >= a) & (T.year <= b)], BASE); add(f"期間 {a}〜{b}年", m)
top50 = T.groupby("iso3").x.sum().nlargest(50).index
m, _ = ppml(T[T.iso3.isin(top50)], BASE); add("輸出額の上位50か国に絞る", m)
m, _ = ppml(T.dropna(subset=["lgdp_wb"]), BASE.replace("lgdp", "lgdp_wb"))
rob.append({"name": "GDP を世界銀行の値にする", **{f"{v}_{k}": (coef(m, v.replace("lgdp", "lgdp_wb")) or {}).get(k) for v in ["ldist", "lgdp"] for k in ["b", "lo", "hi"]}, "note": ""})
m, _ = ppml(T[~T.iso3.isin(["USA", "CHN"])], BASE); add("米国と中国を除く", m)
m, _ = ppml(T, BASE + " + lgdppc"); add("1人あたり GDP を加える", m)
add("地域の固定効果を加える", m1r)
m, _ = ppml(T, "lgdp + ldist + landlocked + C(year)"); add("EPA の変数を除く", m)
pd.DataFrame(rob).to_csv(os.path.join(R, "robustness.csv"), index=False)
out["robust"] = rob
out["by_commodity"] = cm
yrdf = pd.DataFrame(yr)
out["dist_by_year_first5"] = round(float(yrdf[yrdf.year <= 2004].dist_b.mean()), 3)
out["dist_by_year_last5"] = round(float(yrdf[yrdf.year >= 2020].dist_b.mean()), 3)
json.dump(out, open(os.path.join(R, "results.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps({k: v for k, v in out.items() if k not in ("robust", "by_commodity")}, ensure_ascii=False, indent=1))
print(pd.DataFrame(rob)[["name", "ldist_b", "ldist_lo", "ldist_hi", "lgdp_b"]].to_string())
print(pd.DataFrame(cm)[["name", "years", "share_zero", "lgdp", "ldist", "ldist_lo", "ldist_hi", "epa", "r2_level", "r2_log_pos"]].to_string())
print(yrdf.to_string())
print(rr.head(25).to_string())

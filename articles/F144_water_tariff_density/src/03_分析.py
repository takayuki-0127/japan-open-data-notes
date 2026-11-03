"""03 分析：水道料金（家庭用10m3・口径13mm）の差を、規模・密度・水源でどこまで説明できるか。
主: 令和6年度・上水道の末端給水事業（給水形態=1）。
出力: results/*.csv, results/summary.json
"""
import json, itertools, math
from pathlib import Path
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import KFold, cross_val_predict

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
SEED = 20261103
rng = np.random.default_rng(SEED)


def prep(df, keitai=("1",)):
    d = df[df["keitai"].astype(str).isin(keitai)].copy()
    d = d[(d["fee10"] > 0) & (d["pop_served"] > 0) & (d["pipe_km"] > 0) & (d["intake_cap"] > 0)]
    d["l_fee"] = np.log(d["fee10"])
    d["l_price"] = np.log(d["supply_price"])
    d["l_cost"] = np.log(d["supply_cost"])
    d["l_pop"] = np.log(d["pop_served"])
    d["l_dens"] = np.log(d["dens_pipe"])
    d["l_vol"] = np.log(d["annual_rev_water"])
    d["l_vdens"] = np.log(d["annual_rev_water"] * 1000 / d["pipe_km"] / 1000)  # 千m3/km
    d["yushu"] = d["yushu_rate"] / 100
    d["recov"] = d["supply_price"] / d["supply_cost"]
    return d.dropna(subset=["l_fee", "l_pop", "l_dens", "sh_dam", "sh_surface", "sh_bulk"])


BLOCKS = {
    "規模": ["l_pop"],
    "密度": ["l_dens"],
    "水源": ["sh_dam", "sh_surface", "sh_bulk"],
}
MAIN = "l_fee ~ l_pop + l_dens + sh_dam + sh_surface + sh_bulk"


def r2(d, y, xs):
    if not xs:
        return 0.0
    return smf.ols(f"{y} ~ " + " + ".join(xs), data=d).fit().rsquared


def shapley(d, y, blocks):
    names = list(blocks)
    out = {}
    for b in names:
        others = [n for n in names if n != b]
        val = 0.0
        for k in range(len(others) + 1):
            for S in itertools.combinations(others, k):
                w = (math.factorial(k) * math.factorial(len(names) - k - 1)
                     / math.factorial(len(names)))
                xs = sum((blocks[s] for s in S), [])
                val += w * (r2(d, y, xs + blocks[b]) - r2(d, y, xs))
        out[b] = val
    return out


def fit(d, formula, fe=False):
    f = formula + (" + C(pref)" if fe else "")
    return smf.ols(f, data=d).fit(cov_type="HC1")


def coefs(m, keys=("l_pop", "l_dens", "sh_dam", "sh_surface", "sh_bulk")):
    rows = {}
    ci = m.conf_int()
    for k in keys:
        if k in m.params:
            rows[k] = (m.params[k], ci.loc[k, 0], ci.loc[k, 1])
    return rows


r06 = pd.read_csv(ROOT / "data/water_R06.csv", dtype={"keitai": str})
r01 = pd.read_csv(ROOT / "data/water_R01.csv", dtype={"keitai": str})
d = prep(r06)
S = {"n": int(len(d))}

# --- 1. 料金の分布 ---
S["fee_median"] = float(d["fee10"].median())
S["fee_p5"], S["fee_p95"] = map(float, d["fee10"].quantile([0.05, 0.95]))
S["fee_min"], S["fee_max"] = float(d["fee10"].min()), float(d["fee10"].max())
S["fee_ratio_p95_p5"] = S["fee_p95"] / S["fee_p5"]
S["var_lfee"] = float(d["l_fee"].var())

# --- 2. 主モデル ---
m = fit(d, MAIN)
S["main_r2"] = float(m.rsquared)
S["main_adj_r2"] = float(m.rsquared_adj)
S["main_coef"] = {k: list(map(float, v)) for k, v in coefs(m).items()}
pd.DataFrame({"coef": m.params, "lo": m.conf_int()[0], "hi": m.conf_int()[1], "p": m.pvalues}).to_csv(RES / "main_ols.csv")

# 規模の2乗（規模の経済が途中で止まるか）
m2 = fit(d, MAIN + " + I(l_pop**2)")
S["quad_pop"] = [float(m2.params["I(l_pop ** 2)"]), float(m2.pvalues["I(l_pop ** 2)"])]
S["quad_r2"] = float(m2.rsquared)

# --- 3. Shapley 分解 ---
sh = shapley(d, "l_fee", BLOCKS)
S["shapley"] = {k: float(v) for k, v in sh.items()}
# 都道府県（同じ県の中か、県の間か）
fe_only = smf.ols("l_fee ~ C(pref)", data=d).fit()
S["pref_only_r2"] = float(fe_only.rsquared)
mfe = fit(d, MAIN, fe=True)
S["main_fe_r2"] = float(mfe.rsquared)
S["main_fe_coef"] = {k: list(map(float, v)) for k, v in coefs(mfe).items()}
# 残差のうち県の間で説明できる割合
d["resid"] = m.resid
S["resid_pref_share"] = float(smf.ols("resid ~ C(pref)", data=d).fit().rsquared)

# --- 4. 予測の上限（非線形を許したら）---
X = d[["l_pop", "l_dens", "sh_dam", "sh_surface", "sh_bulk"]].values
y = d["l_fee"].values
kf = KFold(5, shuffle=True, random_state=SEED)
p_lin = cross_val_predict(LinearRegression(), X, y, cv=kf)
p_gb = cross_val_predict(GradientBoostingRegressor(random_state=SEED, n_estimators=300, max_depth=3,
                                                   learning_rate=0.05, subsample=0.8), X, y, cv=kf)
def cvr2(p):
    return float(1 - ((y - p) ** 2).sum() / ((y - y.mean()) ** 2).sum())
S["cv_r2_lin"], S["cv_r2_gbm"] = cvr2(p_lin), cvr2(p_gb)
X2 = np.column_stack([X, d["yushu"].values, d["old_pipe_sh"].fillna(d["old_pipe_sh"].median()).values,
                      d["recov"].values])
p_gb2 = cross_val_predict(GradientBoostingRegressor(random_state=SEED, n_estimators=300, max_depth=3,
                                                    learning_rate=0.05, subsample=0.8), X2, y, cv=kf)
S["cv_r2_gbm_plus"] = cvr2(p_gb2)

# --- 5. 費用関数（給水原価）---
mc = fit(d, "l_cost ~ l_vol + l_vdens + sh_dam + sh_surface + sh_bulk")
S["cost_r2"] = float(mc.rsquared)
S["cost_coef"] = {k: list(map(float, v)) for k, v in coefs(mc, ("l_vol", "l_vdens", "sh_dam", "sh_surface", "sh_bulk")).items()}
mcp = fit(d, "l_price ~ l_vol + l_vdens + sh_dam + sh_surface + sh_bulk")
S["price_r2"] = float(mcp.rsquared)
S["price_coef"] = {k: list(map(float, v)) for k, v in coefs(mcp, ("l_vol", "l_vdens", "sh_dam", "sh_surface", "sh_bulk")).items()}
# 料金回収率（供給単価/給水原価）
S["recov_median"] = float(d["recov"].median())
S["recov_below1_share"] = float((d["recov"] < 1).mean())

# 密度5分位
d["dq"] = pd.qcut(d["dens_pipe"], 5, labels=[f"Q{i}" for i in range(1, 6)])
cc = ["c_depr", "c_labor", "c_bulk", "c_interest", "c_repair", "c_contract", "c_power", "c_chem", "c_total"]
qtab = d.groupby("dq", observed=True).agg(
    n=("fee10", "size"), dens_med=("dens_pipe", "median"), pop_med=("pop_served", "median"),
    fee_med=("fee10", "median"), price_med=("supply_price", "median"), cost_med=("supply_cost", "median"),
    recov_med=("recov", "median"), price_mean=("supply_price", "mean"), cost_mean=("supply_cost", "mean"),
    **{c: (c, "median") for c in cc}, **{c + "_mean": (c, "mean") for c in cc})
qtab.to_csv(RES / "density_quintiles.csv")
S["dq_fee_med"] = qtab["fee_med"].round(0).tolist()
S["dq_cost_med"] = qtab["cost_med"].round(1).tolist()
S["dq_dens_med"] = qtab["dens_med"].round(1).tolist()
S["dq_recov_med"] = qtab["recov_med"].round(3).tolist()

# 主な水源（取水能力の過半）別
def main_src(r):
    v = {"地下水等": r.sh_ground, "ダム": r.sh_dam, "ダム以外の表流水": r.sh_surface, "受水": r.sh_bulk}
    k = max(v, key=v.get)
    return k if v[k] >= 0.5 else "混合"
d["src"] = d.apply(main_src, axis=1)
src = d.groupby("src").agg(n=("fee10", "size"), fee_med=("fee10", "median"),
                           pop_med=("pop_served", "median"), dens_med=("dens_pipe", "median"))
# 規模・密度をそろえた水源の差（地下水等=基準）
ms = fit(d, "l_fee ~ l_pop + l_dens + C(src, Treatment('地下水等'))")
adj = {}
for k in src.index:
    key = f"C(src, Treatment('地下水等'))[T.{k}]"
    if key in ms.params:
        adj[k] = (float(np.exp(ms.params[key]) - 1), float(np.exp(ms.conf_int().loc[key, 0]) - 1),
                  float(np.exp(ms.conf_int().loc[key, 1]) - 1))
    else:
        adj[k] = (0.0, 0.0, 0.0)
src["adj_diff"] = [adj[k][0] for k in src.index]
src["adj_lo"] = [adj[k][1] for k in src.index]
src["adj_hi"] = [adj[k][2] for k in src.index]
src.to_csv(RES / "by_source.csv")
S["by_source"] = src.round(3).reset_index().to_dict("records")

# 2つの事業を比べた例：密度が10倍
S["dens_x10_pct"] = float(np.exp(m.params["l_dens"] * np.log(10)) - 1)
S["pop_x10_pct"] = float(np.exp(m.params["l_pop"] * np.log(10)) - 1)
S["dens_x2_pct"] = float(np.exp(m.params["l_dens"] * np.log(2)) - 1)

# --- 6. 頑健性 ---
rob = []
def add(name, dd, formula=MAIN, fe=False, y="l_fee"):
    mm = fit(dd, formula.replace("l_fee", y), fe=fe)
    c = coefs(mm)
    rob.append({"check": name, "n": int(mm.nobs), "r2": mm.rsquared,
                "b_pop": c["l_pop"][0], "b_dens": c["l_dens"][0], "b_dens_lo": c["l_dens"][1], "b_dens_hi": c["l_dens"][2],
                "b_dam": c["sh_dam"][0], "b_surface": c["sh_surface"][0], "b_bulk": c["sh_bulk"][0]})
add("主（R6・上水道末端）", d)
add("令和元年度", prep(r01))
add("簡易水道（法適用）を含む", prep(r06, ("1", "5")))
add("供給単価（円/m3）を結果に", d, y="l_price")
q = d["l_fee"].quantile([0.01, 0.99])
add("料金の上下1%を除く", d[(d.l_fee > q.iloc[0]) & (d.l_fee < q.iloc[1])])
add("給水人口5千人以上", d[d.pop_served >= 5000])
add("都道府県の固定効果", d, fe=True)
dh = d[d["dens_hab"].notna() & (d["dens_hab"] > 0)].copy()
dh["l_dens"] = np.log(dh["dens_hab"])
add("密度=可住地面積あたり給水人口（市町村営のみ）", dh)
add("有収率と老朽管の割合を加える", d.assign(old=d.old_pipe_sh.fillna(d.old_pipe_sh.median())), MAIN + " + yushu + old")
rob = pd.DataFrame(rob)
rob.to_csv(RES / "robustness.csv", index=False)
S["robustness"] = rob.round(4).to_dict("records")

# Shapley の頑健性（R01・簡易水道含む）
S["shapley_R01"] = {k: float(v) for k, v in shapley(prep(r01), "l_fee", BLOCKS).items()}
S["shapley_with_simple"] = {k: float(v) for k, v in shapley(prep(r06, ("1", "5")), "l_fee", BLOCKS).items()}
S["shapley_price"] = {k: float(v) for k, v in shapley(d, "l_price", BLOCKS).items()}

# 設計の代替案：都道府県平均（給水人口で重みづけ）
pa = d.groupby("pref").apply(lambda g: pd.Series({
    "l_fee": np.log(np.average(g.fee10, weights=g.pop_served)),
    "l_pop": np.log(g.pop_served.sum() / len(g)),
    "l_dens": np.log(g.pop_served.sum() / g.pipe_km.sum()),
    "sh_dam": np.average(g.sh_dam, weights=g.intake_cap),
    "sh_surface": np.average(g.sh_surface, weights=g.intake_cap),
    "sh_bulk": np.average(g.sh_bulk, weights=g.intake_cap)}))
mp = smf.ols(MAIN, data=pa).fit(cov_type="HC1")
S["pref_avg"] = {"n": int(len(pa)), "r2": float(mp.rsquared),
                 "b_dens": float(mp.params["l_dens"]), "b_dens_p": float(mp.pvalues["l_dens"]),
                 "b_pop": float(mp.params["l_pop"])}

# ブートストラップ（Shapley の区間）
B = 300
bs = []
idx = np.arange(len(d))
for b in range(B):
    s = d.iloc[rng.choice(idx, len(idx), replace=True)]
    bs.append(shapley(s, "l_fee", BLOCKS))
bs = pd.DataFrame(bs)
S["shapley_ci"] = {k: [float(bs[k].quantile(0.025)), float(bs[k].quantile(0.975))] for k in bs}
S["main_r2_ci"] = [float(bs.sum(axis=1).quantile(0.025)), float(bs.sum(axis=1).quantile(0.975))]

d[["pref", "keiei", "fee10", "supply_price", "supply_cost", "pop_served", "dens_pipe", "sh_dam", "sh_surface",
   "sh_bulk", "sh_ground", "src", "dq", "recov"]].assign(pred=np.exp(m.fittedvalues)).to_csv(
    RES / "analysis_rows_noname.csv", index=False)

json.dump(S, open(RES / "summary.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps({k: S[k] for k in ["n", "fee_median", "fee_p5", "fee_p95", "main_r2", "main_coef", "shapley",
                                     "shapley_ci", "pref_only_r2", "main_fe_r2", "resid_pref_share", "cv_r2_lin",
                                     "cv_r2_gbm", "cv_r2_gbm_plus", "cost_coef", "cost_r2", "dq_fee_med", "dq_cost_med",
                                     "dq_dens_med", "dq_recov_med", "recov_median", "recov_below1_share",
                                     "dens_x10_pct", "pop_x10_pct", "dens_x2_pct", "quad_pop", "pref_avg",
                                     "shapley_R01", "shapley_with_simple", "shapley_price"]},
                 ensure_ascii=False, indent=1))
print(src)
print(rob.round(3).to_string())

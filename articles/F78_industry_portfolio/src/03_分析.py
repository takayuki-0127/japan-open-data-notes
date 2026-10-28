"""03 分析：産業の多様性・産業ポートフォリオのリスクと、雇用の落ち方・ぶれ方"""
import json
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from common import DATA, RAW, RES, SEED

rng = np.random.default_rng(SEED)
ind = pd.read_csv(RAW / "industries.csv", index_col=0)["industry"]
codes = list(ind.index)
m = pd.read_csv(DATA / "municipal.csv", dtype={"code": str, "pref": str})


def wins(s, p=0.01):
    lo, hi = s.quantile([p, 1 - p])
    return s.clip(lo, hi)


def shares(df, y):
    X = df[[f"{c}_{y}" for c in codes]].fillna(0).to_numpy()
    return X / X.sum(axis=1, keepdims=True), X


S16, X16 = shares(m, 2016)
S14, X14 = shares(m, 2014)
_, X21 = shares(m, 2021)
nat16, nat14, nat21 = X16.sum(0), X14.sum(0), X21.sum(0)
s_nat = nat16 / nat16.sum()

# 多様性の指標（2016年の産業シェア）
m["hhi"] = (S16 ** 2).sum(1)
m["eff_n"] = 1 / m["hhi"]  # 実質的な産業の数
with np.errstate(divide="ignore", invalid="ignore"):
    m["entropy"] = -np.nansum(np.where(S16 > 0, S16 * np.log(S16), 0), axis=1)
m["krugman"] = np.abs(S16 - s_nat).sum(1)
m["top_share"] = S16.max(1)
m["top_ind"] = [ind.iloc[i] for i in S16.argmax(1)]
m["log_pop"] = np.log(m["pop2015"])
m["ln_eff"] = np.log(m["eff_n"])

# 雇用の伸び（%、対数×100）
m["g"] = wins(100 * np.log(m["tot2021"] / m["tot2016"]))
m["g0"] = wins(100 * np.log(m["tot2016"] / m["tot2014"]))

# バーティク：自分を除いた全国の産業別の伸び × 2016年のシェア
G_loo = 100 * np.log((nat21 - X21) / np.maximum(nat16 - X16, 1))
m["bartik"] = (S16 * G_loo).sum(1)
G0_loo = 100 * np.log((nat16 - X16) / np.maximum(nat14 - X14, 1))
m["bartik0"] = (S14 * G0_loo).sum(1)
m["u"] = m["g"] - m["bartik"]  # 産業構成では説明できない、その町だけの動き
m["abs_u"] = m["u"].abs()
m["drop10"] = (m["g"] < -10).astype(int)
m["shr_hotel"] = S16[:, codes.index("C220847")]
m["shr_mfg"] = S16[:, codes.index("C220837")]

# ポートフォリオ：町ごとの産業別の伸びのばらつき（産業間の相関も入れる）から「その町に来うる、町独自のぶれ」を出す
# 産業 j の町レベルの伸び（2016年に30人以上いる町だけ）、全国の伸びとの差
G_nat = 100 * np.log(nat21 / nat16)
with np.errstate(divide="ignore", invalid="ignore"):
    gij = 100 * np.log(X21 / X16) - G_nat
valid = (X16 >= 30) & np.isfinite(gij)
gij = np.where(valid, gij, np.nan)
# 各産業の上下1%を丸める
for j in range(len(codes)):
    col = gij[:, j]
    ok = np.isfinite(col)
    if ok.sum() > 50:
        lo, hi = np.nanquantile(col, [0.01, 0.99])
        gij[ok, j] = np.clip(col[ok], lo, hi)
gdf = pd.DataFrame(gij, columns=codes)
cov = gdf.cov(min_periods=200).to_numpy()  # 産業の組ごとに、両方30人以上いる町で計算
cov = np.nan_to_num(cov)
# 半正定値に直す
w, V = np.linalg.eigh(cov)
cov_psd = (V * np.clip(w, 0, None)) @ V.T
sd_ind = np.sqrt(np.diag(cov_psd))
corr_ind = cov_psd / np.outer(sd_ind, sd_ind)
m["port_sd"] = np.sqrt(np.einsum("ij,jk,ik->i", S16, cov_psd, S16))
m["port_sd_indep"] = np.sqrt((S16 ** 2 * np.diag(cov_psd)).sum(1))


def ols(formula, data, cluster=True, weights=None):
    if weights is not None:
        mod = smf.wls(formula, data=data, weights=data[weights])
    else:
        mod = smf.ols(formula, data=data)
    if cluster:
        return mod.fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(data["pref"])[0]})
    return mod.fit(cov_type="HC3")


def coef(r, name):
    b = r.params[name]
    lo, hi = r.conf_int().loc[name]
    return {"b": round(float(b), 3), "lo": round(float(lo), 3), "hi": round(float(hi), 3),
            "p": round(float(r.pvalues[name]), 4), "n": int(r.nobs)}


ctrl = "log_pop + old15 + work15 + C(pref)"
res = {}
d = m.dropna(subset=["g", "bartik", "ln_eff", "old15", "work15"]).copy()
d["z_eff"] = (d["ln_eff"] - d["ln_eff"].mean()) / d["ln_eff"].std()
d["z_port"] = (d["port_sd"] - d["port_sd"].mean()) / d["port_sd"].std()

res["n"] = int(len(d))
res["summary"] = {
    "eff_n_median": round(float(d["eff_n"].median()), 2),
    "eff_n_p10": round(float(d["eff_n"].quantile(.1)), 2),
    "eff_n_p90": round(float(d["eff_n"].quantile(.9)), 2),
    "top_share_median": round(float(d["top_share"].median()), 3),
    "corr_effn_logpop": round(float(d[["ln_eff", "log_pop"]].corr().iloc[0, 1]), 3),
    "g_median": round(float(d["g"].median()), 2),
    "g_nat": round(float(100 * np.log(nat21.sum() / nat16.sum())), 2),
    "share_drop10": round(float(d["drop10"].mean()), 3),
    "corr_bartik_g": round(float(d[["bartik", "g"]].corr().iloc[0, 1]), 3),
    "var_share_bartik": round(float(np.corrcoef(d["bartik"], d["g"])[0, 1] ** 2), 3),
    "port_sd_median": round(float(d["port_sd"].median()), 2),
    "port_sd_indep_median": round(float(d["port_sd_indep"].median()), 2),
}
# 1 平均的な伸び：多様性は平均を上げるか（産業構成＝バーティクをそろえて）
r1a = ols(f"g ~ z_eff + {ctrl}", d)
r1b = ols(f"g ~ z_eff + bartik + {ctrl}", d)
res["mean_growth"] = {"eff_only": coef(r1a, "z_eff"), "eff_with_bartik": coef(r1b, "z_eff"),
                      "bartik": coef(r1b, "bartik")}
# 2 ぶれの大きさ：その町だけの動き |u| は、多様な町ほど小さいか
r2a = ols(f"abs_u ~ z_eff + {ctrl}", d)
r2b = ols(f"abs_u ~ z_port + {ctrl}", d)
r2c = ols(f"abs_u ~ z_eff + z_port + {ctrl}", d)
res["abs_dev"] = {"eff": coef(r2a, "z_eff"), "port": coef(r2b, "z_port"),
                  "both_eff": coef(r2c, "z_eff"), "both_port": coef(r2c, "z_port"),
                  "mean_abs_u": round(float(d["abs_u"].mean()), 2)}
# 3 大きく落ちる確率（−10%より悪い）：線形確率モデル
r3 = ols(f"drop10 ~ z_eff + bartik + {ctrl}", d)
res["drop10"] = {"eff": coef(r3, "z_eff"), "bartik": coef(r3, "bartik")}
# 4 予測したぶれと実際のぶれ（分位ごと）
d["port_q"] = pd.qcut(d["port_sd"], 5, labels=False)
d["eff_q"] = pd.qcut(d["eff_n"], 5, labels=False)
tab = d.groupby("eff_q").agg(eff_n=("eff_n", "median"), pop=("pop2015", "median"),
                             g_mean=("g", "mean"), g_sd=("g", "std"), abs_u=("abs_u", "mean"),
                             drop10=("drop10", "mean"), n=("g", "size")).round(3)
tab.to_csv(RES / "by_diversity_quintile.csv")
tab2 = d.groupby("port_q").agg(port_sd=("port_sd", "median"), u_sd=("u", "std"), abs_u=("abs_u", "mean"),
                               n=("u", "size")).round(3)
tab2.to_csv(RES / "by_portfolio_quintile.csv")
res["port_vs_actual_corr"] = round(float(np.corrcoef(tab2["port_sd"], tab2["u_sd"])[0, 1]), 3)
# 規模の帯ごとに（多様性と人口が強く相関するので）
d["size_bin"] = pd.cut(d["pop2015"], [0, 5000, 20000, 100000, 1e8], labels=["5千未満", "5千〜2万", "2万〜10万", "10万以上"])
sb = {}
for b, g in d.groupby("size_bin", observed=True):
    if len(g) < 60:
        continue
    rr = smf.ols("abs_u ~ z_eff + log_pop + old15 + work15", data=g).fit(cov_type="HC3")
    sb[str(b)] = coef(rr, "z_eff")
res["abs_dev_by_size"] = sb

# 5 平常時（2014→16）との比較
d0 = d.dropna(subset=["g0", "bartik0"]).copy()
d0["u0"] = d0["g0"] - d0["bartik0"]
d0["abs_u0"] = d0["u0"].abs()
r5 = ols(f"abs_u0 ~ z_eff + {ctrl}", d0)
r5m = ols(f"g0 ~ z_eff + bartik0 + {ctrl}", d0)
res["normal_period"] = {"abs_dev_eff": coef(r5, "z_eff"), "mean_eff": coef(r5m, "z_eff"),
                        "mean_abs_u0": round(float(d0["abs_u0"].mean()), 2)}

# 6 頑健性
rob = []
def add(name, r, var):
    c = coef(r, var); c["setting"] = name; rob.append(c)
d["z_ent"] = (d["entropy"] - d["entropy"].mean()) / d["entropy"].std()
d["z_kru"] = -(d["krugman"] - d["krugman"].mean()) / d["krugman"].std()  # 全国に近いほど＋
add("基本（実質的な産業の数）", r2a, "z_eff")
add("エントロピー", ols(f"abs_u ~ z_ent + {ctrl}", d), "z_ent")
add("全国との近さ（クルーグマン指数の逆）", ols(f"abs_u ~ z_kru + {ctrl}", d), "z_kru")
add("人口5千人以上", ols(f"abs_u ~ z_eff + {ctrl}", d[d.pop2015 >= 5000]), "z_eff")
add("都道府県の固定効果なし", ols("abs_u ~ z_eff + log_pop + old15 + work15", d), "z_eff")
add("人口で重みづけ", ols(f"abs_u ~ z_eff + {ctrl}", d, weights="pop2015"), "z_eff")
q90 = d["shr_hotel"].quantile(.9)
add("宿泊・飲食の割合が上位10%の町を除く", ols(f"abs_u ~ z_eff + {ctrl}", d[d.shr_hotel < q90]), "z_eff")
add("製造業の割合を統制", ols(f"abs_u ~ z_eff + shr_mfg + shr_hotel + {ctrl}", d), "z_eff")
add("結果を二乗（分散）に", ols(f"I(u**2) ~ z_eff + {ctrl}", d), "z_eff")
add("平常時 2014→16", r5, "z_eff")
pd.DataFrame(rob).to_csv(RES / "robustness.csv", index=False)
res["robustness"] = rob

# 7 都道府県（モデル推計値の就業者、2002〜2025）
emp = pd.read_csv(DATA / "pref_employment_lfs.csv", index_col=0)
lg = 100 * np.log(emp).diff()
pref_div = []
for p, g in m.groupby("pref"):
    x16 = g[[f"{c}_2016" for c in codes]].fillna(0).sum().to_numpy()
    s = x16 / x16.sum()
    pref_div.append({"pref": p, "eff_n": 1 / (s ** 2).sum(), "shr_mfg": s[codes.index("C220837")],
                     "shr_hotel": s[codes.index("C220847")]})
pdv = pd.DataFrame(pref_div).set_index("pref")
pdv.index = [f"{int(i):02d}" for i in pdv.index]
pdv["lehman"] = 100 * np.log(emp.loc[2010] / emp.loc[2008])
pdv["covid"] = 100 * np.log(emp.loc[2021] / emp.loc[2019])
pdv["vol"] = lg.loc[2003:2019].std()
pdv["ln_eff"] = np.log(pdv["eff_n"])
pdv["log_emp"] = np.log(emp.loc[2016])
pdv.round(4).to_csv(RES / "pref47.csv")
pr = {}
for y in ["lehman", "covid", "vol"]:
    r = smf.ols(f"{y} ~ ln_eff + log_emp", data=pdv).fit(cov_type="HC3")
    r2 = smf.ols(f"{y} ~ ln_eff + log_emp + shr_mfg + shr_hotel", data=pdv).fit(cov_type="HC3")
    pr[y] = {"corr": round(float(pdv[[y, "ln_eff"]].corr().iloc[0, 1]), 3), "ln_eff": coef(r, "ln_eff"),
             "ln_eff_with_mix": coef(r2, "ln_eff"), "mean": round(float(pdv[y].mean()), 2)}
pr["corr_lehman_mfg"] = round(float(pdv[["lehman", "shr_mfg"]].corr().iloc[0, 1]), 3)
pr["corr_covid_hotel"] = round(float(pdv[["covid", "shr_hotel"]].corr().iloc[0, 1]), 3)
res["prefecture"] = pr

# 産業の相関（ポートフォリオの材料）
corr_df = pd.DataFrame(corr_ind, index=ind.values, columns=ind.values).round(3)
corr_df.to_csv(RES / "industry_corr.csv")
pd.DataFrame({"industry": ind.values, "nat_growth_16_21": np.round(G_nat, 2), "town_sd": np.round(sd_ind, 2),
              "nat_share_2016": np.round(s_nat, 4)}).to_csv(RES / "industry_stats.csv", index=False)
off = corr_ind[np.triu_indices(len(codes), 1)]
res["industry_corr_mean"] = round(float(np.mean(off)), 3)
d[["code", "pref", "pop2015", "eff_n", "entropy", "krugman", "top_share", "g", "g0", "bartik", "u", "port_sd",
   "port_sd_indep", "drop10", "shr_hotel", "shr_mfg"]].round(4).to_csv(RES / "municipal_analysis.csv", index=False)
json.dump(res, open(RES / "results.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False, indent=1)[:6000])

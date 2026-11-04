"""03 分析：宅配便の個数を、ネット通販（家計消費状況調査）・人口・単独世帯でどこまで説明できるか。"""
import json, itertools, warnings
warnings.filterwarnings("ignore")
from pathlib import Path
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.stattools import adfuller

ROOT = Path(__file__).resolve().parents[1]
DATA, RES = ROOT / "data", ROOT / "results"
RES.mkdir(exist_ok=True)
np.random.seed(185)
d = pd.read_csv(DATA / "fy_panel.csv")
d = d[(d.fy >= 2004) & (d.fy <= 2024)].reset_index(drop=True)
d["lP"] = np.log(d.parcels_adj_mil); d["lPraw"] = np.log(d.parcels_total_mil)
d["lN"] = np.log(d.net_spend); d["lNcy"] = np.log(d.net_spend_cy); d["lS"] = np.log(d.net_share)
d["lPOP"] = np.log(d.pop_total); d["lH"] = np.log(d.one_person_thou); d["t"] = d.fy - 2004
d["D"] = d.newdef_frac; d["Dcy"] = d.newdef_cy
d["lG"] = np.log(d.goods_fy)
S = {}


def ols(y, X, df, hac=True):
    Xc = sm.add_constant(df[X]) if X else np.ones((len(df), 1))
    m = sm.OLS(df[y], Xc, missing="drop")
    return m.fit(cov_type="HAC", cov_kwds={"maxlags": 2}) if hac else m.fit()


# 1) 全体の動き
a, b = d.iloc[0], d.iloc[-1]
S["overview"] = {"fy0": 2004, "fy1": 2024, "P0": a.parcels_adj_mil, "P1": b.parcels_adj_mil,
                 "P_growth_pct": (b.parcels_adj_mil / a.parcels_adj_mil - 1) * 100,
                 "Praw0": a.parcels_total_mil, "N0": a.net_spend, "N1": b.net_spend,
                 "share0": a.net_share / 100, "share1": b.net_share / 100,
                 "pop_growth_pct": (b.pop_total / a.pop_total - 1) * 100,
                 "H_growth_pct": (b.one_person_thou / a.one_person_thou - 1) * 100,
                 "pc0": a.parcels_per_capita, "pc1": b.parcels_per_capita}

# 2) 定義の切れ目をつなぐ：FY2014・2015 の伸びを、前後3年の平均の伸びで置きかえる（つなぎ方A）
dl = d.lN.diff()
brk = d.fy.isin([2014, 2015])
fill = np.mean([dl[d.fy.isin([2011, 2012, 2013])].mean(), dl[d.fy.isin([2016, 2017, 2018])].mean()])
dl_spl = dl.where(~brk, fill)
d["lN_spl"] = d.lN.iloc[0] + dl_spl.fillna(0).cumsum()
# つなぎ方B：2015年の22品目計と旧「支出総額」の比を、注文世帯の割合の伸びで推定（2014→2015 の割合の伸びだけ金額も伸びたとみなす）
r_share = d.loc[d.fy == 2015, "net_share"].item() / d.loc[d.fy == 2014, "net_share"].item()
dl_b = dl.copy(); dl_b[d.fy == 2014] = np.log(r_share) * 0.25 + dl[d.fy == 2013].item() * 0.75
dl_b[d.fy == 2015] = np.log(r_share) * 0.75
d["lN_splB"] = d.lN.iloc[0] + dl_b.fillna(0).cumsum()
S["splice"] = {"fill_growth": float(fill), "ratio_new_to_old_A": float(np.exp(dl[brk].sum() - 2 * fill)),
               "net_growth_x_A": float(np.exp(d.lN_spl.iloc[-1] - d.lN_spl.iloc[0])),
               "net_growth_x_B": float(np.exp(d.lN_splB.iloc[-1] - d.lN_splB.iloc[0])),
               "net_growth_x_raw": float(b.net_spend / a.net_spend)}

# 3) 差分（前年度比）の回帰：主分析
dd = d[["fy"]].copy()
for c in ["lP", "lPraw", "lN", "lN_spl", "lS", "lPOP", "lH", "D", "lG", "lNcy", "Dcy"]:
    dd["d" + c] = d[c].diff()
dd = dd.dropna(subset=["dlP"])
main = ols("dlP", ["dlN", "dD"], dd)
S["diff_main"] = {"beta_net": main.params["dlN"], "se": main.bse["dlN"], "p": main.pvalues["dlN"],
                  "r2": main.rsquared, "n": int(main.nobs), "const": main.params["const"]}
# 変数の組み合わせ（差分）
rows = []
cands = {"ネット支出": "dlN", "注文世帯の割合": "dlS", "人口": "dlPOP", "単独世帯": "dlH"}
for k in range(0, 5):
    for comb in itertools.combinations(cands, k):
        X = [cands[c] for c in comb] + (["dD"] if "ネット支出" in comb else [])
        m = ols("dlP", X, dd)
        rows.append({"vars": "＋".join(comb) if comb else "定数だけ", "k": k, "r2": m.rsquared, "adj_r2": m.rsquared_adj, "aic": m.aic,
                     "beta_net": m.params.get("dlN", np.nan), "p_net": m.pvalues.get("dlN", np.nan),
                     "beta_share": m.params.get("dlS", np.nan), "p_share": m.pvalues.get("dlS", np.nan),
                     "beta_H": m.params.get("dlH", np.nan), "p_H": m.pvalues.get("dlH", np.nan),
                     "beta_pop": m.params.get("dlPOP", np.nan), "p_pop": m.pvalues.get("dlPOP", np.nan)})
combo = pd.DataFrame(rows); combo.to_csv(RES / "diff_combinations.csv", index=False)

# 4) 水準の回帰（長い関係）
lv = []
for name, X in [("ネット支出だけ", ["lN", "D"]), ("ネット＋人口＋単独世帯", ["lN", "D", "lPOP", "lH"]), ("単独世帯＋人口だけ", ["lPOP", "lH"]),
                ("トレンドだけ", ["t"]), ("ネット＋トレンド", ["lN", "D", "t"]), ("注文世帯の割合だけ", ["lS"])]:
    m = ols("lP", X, d)
    adf_p = adfuller(m.resid, maxlag=1, autolag=None)[1]
    lv.append({"model": name, "r2": m.rsquared, "beta_net": m.params.get("lN", np.nan), "p_net": m.pvalues.get("lN", np.nan),
               "beta_share": m.params.get("lS", np.nan), "beta_H": m.params.get("lH", np.nan), "p_H": m.pvalues.get("lH", np.nan),
               "dw": sm.stats.durbin_watson(m.resid), "resid_adf_p": adf_p, "aic": m.aic})
lv = pd.DataFrame(lv); lv.to_csv(RES / "level_models.csv", index=False)

# 5) 増えた分のうち、ネット支出で説明できる割合（差分の弾力性 × つないだネット支出の伸び）
tot = d.lP.iloc[-1] - d.lP.iloc[0]
beta = main.params["dlN"]
expl = {}
for nm, col in [("A", "lN_spl"), ("B", "lN_splB")]:
    gN = d[col].iloc[-1] - d[col].iloc[0]
    expl[nm] = {"net_contrib_log": beta * gN, "share_of_growth_pct": beta * gN / tot * 100}
const_part = main.params["const"] * (len(d) - 1)
S["decomp"] = {"total_log": tot, "beta": beta, "by_splice": expl, "const_part_log": const_part,
               "const_share_pct": const_part / tot * 100}

# 6) 予測で確かめる：前半（FY2005〜2014）で推定し、後半（FY2016〜2024）の伸びを当てる
tr = dd[(dd.fy >= 2005) & (dd.fy <= 2013)]; te = dd[(dd.fy >= 2016)]
m_tr = ols("dlP", ["dlN"], tr)
pred = m_tr.params["const"] + m_tr.params["dlN"] * te.dlN
S["oos"] = {"beta_train": m_tr.params["dlN"], "const_train": m_tr.params["const"], "r2_train": m_tr.rsquared,
            "pred_sum_log": float(pred.sum()), "actual_sum_log": float(te.dlP.sum()),
            "pred_growth_pct": float((np.exp(pred.sum()) - 1) * 100), "actual_growth_pct": float((np.exp(te.dlP.sum()) - 1) * 100),
            "const_only_growth_pct": float((np.exp(tr.dlP.mean() * len(te)) - 1) * 100), "mean_train": float(tr.dlP.mean())}
oos_tab = pd.DataFrame({"fy": te.fy, "actual": te.dlP, "pred": pred}); oos_tab.to_csv(RES / "oos_2016_2024.csv", index=False)

# 7) 頑健性
rob = []
def add(label, df, y, X, key="dlN"):
    m = ols(y, X, df)
    rob.append({"check": label, "n": int(m.nobs), "beta": m.params.get(key, np.nan), "se": m.bse.get(key, np.nan),
                "p": m.pvalues.get(key, np.nan), "r2": m.rsquared})
add("主分析：FY2005〜2024、ゆうパック補正、年度に組み替え", dd, "dlP", ["dlN", "dD"])
add("期間：コロナ前（〜FY2019）", dd[dd.fy <= 2019], "dlP", ["dlN", "dD"])
add("期間：FY2020 を除く", dd[dd.fy != 2020], "dlP", ["dlN", "dD"])
add("期間：FY2008〜（補正の要らない期間）", dd[dd.fy >= 2008], "dlP", ["dlN", "dD"])
add("期間：旧定義だけ（FY2005〜2013）", dd[dd.fy <= 2013], "dlP", ["dlN"])
add("期間：新定義だけ（FY2016〜2024）", dd[dd.fy >= 2016], "dlP", ["dlN"])
add("補正なし（国交省の値そのまま、FY2007 の段差あり）", dd, "dlPraw", ["dlN", "dD"])
add("暦年の年平均（年度に組み替えない）", dd, "dlP", ["dlNcy", "dDcy"], key="dlNcy")
add("つないだネット支出（つなぎ方A）、切れ目の2年を除く", dd[~dd.fy.isin([2014, 2015])], "dlP", ["dlN_spl"], key="dlN_spl")
add("注文世帯の割合（金額の代わり）", dd, "dlP", ["dlS"], key="dlS")
add("モノだけの支出（FY2016〜2024）", dd[dd.fy >= 2016], "dlP", ["dlG"], key="dlG")
add("単独世帯・人口も入れる", dd, "dlP", ["dlN", "dD", "dlH", "dlPOP"])
add("前年のネット支出の伸びも入れる", dd.assign(dlN_l1=dd.dlN.shift(1), dD_l1=dd.dD.shift(1)).dropna(subset=["dlN_l1"]), "dlP", ["dlN", "dD", "dlN_l1", "dD_l1"])
add("トレンドの代わりに前年度の伸び（自己回帰）を入れる", dd.assign(dlP_l1=dd.dlP.shift(1)).dropna(subset=["dlP_l1"]), "dlP", ["dlN", "dD", "dlP_l1"])
for fy in dd.fy:
    m = ols("dlP", ["dlN", "dD"], dd[dd.fy != fy])
    rob.append({"check": f"1年抜き：FY{fy}", "n": int(m.nobs), "beta": m.params["dlN"], "se": m.bse["dlN"], "p": m.pvalues["dlN"], "r2": m.rsquared})
rob = pd.DataFrame(rob); rob.to_csv(RES / "robustness.csv", index=False)
loo = rob[rob.check.str.startswith("1年抜き")]
S["loo"] = {"beta_min": loo.beta.min(), "beta_max": loo.beta.max(), "argmax": loo.loc[loo.beta.idxmax(), "check"],
            "argmin": loo.loc[loo.beta.idxmin(), "check"], "p_max": loo.p.max()}

# 8) 置換検定：前年度比の並びを入れ替えても、同じくらいの相関が出るか
x = dd.dlN.values - dd.dD.values * 0; y = dd.dlP.values
res_x = sm.OLS(dd.dlN, sm.add_constant(dd.dD)).fit().resid.values
res_y = sm.OLS(dd.dlP, sm.add_constant(dd.dD)).fit().resid.values
obs = np.corrcoef(res_x, res_y)[0, 1]
perm = np.array([np.corrcoef(np.random.permutation(res_x), res_y)[0, 1] for _ in range(20000)])
S["perm"] = {"r_obs": obs, "p_two_sided": float((np.abs(perm) >= abs(obs)).mean())}

# 9) 1世帯・1人あたり
d["parcels_per_net10k"] = d.parcels_adj_mil * 1e6 / (d.net_spend * 12 * d.households_thou * 1e3 / 1e4)
S["intensity"] = {"per_net10k_2004": d.parcels_per_net10k.iloc[0], "per_net10k_2014": d.loc[d.fy == 2014, "parcels_per_net10k"].item(),
                  "per_net10k_2015": d.loc[d.fy == 2015, "parcels_per_net10k"].item(), "per_net10k_2024": d.parcels_per_net10k.iloc[-1]}
yy = dd.set_index("fy")
S["fy2020"] = {"dP_pct": (np.exp(yy.loc[2020, "dlP"]) - 1) * 100, "dN_pct": (np.exp(yy.loc[2020, "dlN"]) - 1) * 100,
               "fitted_pct": (np.exp(main.params["const"] + main.params["dlN"] * yy.loc[2020, "dlN"]) - 1) * 100}
S["growth_by_year"] = {int(r.fy): {"dP": float(r.dlP), "dN": float(r.dlN)} for r in dd.itertuples()}
d.to_csv(RES / "fy_panel_with_splices.csv", index=False)
json.dump(S, open(RES / "summary.json", "w"), ensure_ascii=False, indent=1, default=float)
print(json.dumps({k: S[k] for k in ["overview", "splice", "diff_main", "decomp", "oos", "loo", "perm", "intensity", "fy2020"]}, ensure_ascii=False, indent=1, default=lambda v: round(float(v), 4)))
print(combo.round(3).to_string()); print(lv.round(3).to_string()); print(rob.head(13).round(3).to_string())

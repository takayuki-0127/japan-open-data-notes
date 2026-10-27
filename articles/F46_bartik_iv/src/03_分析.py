"""シフトシェア（バーティク）操作変数：雇用の伸び → 転入超過"""
import json, numpy as np, pandas as pd
import statsmodels.api as sm
from linearmodels.iv import IV2SLS
from common import DATA, RES, SEED

rng = np.random.default_rng(SEED)
df = pd.read_csv(DATA / "panel_municipal.csv", dtype={"code": str, "pref": str}).set_index("code")
IND = pd.read_csv(DATA / "industries.csv", index_col=0)["industry"]
K = list(IND.index)

def wins(s, p=0.01):
    lo, hi = s.quantile([p, 1 - p]); return s.clip(lo, hi)

def build(d, base=2016, end=2021, mig=(2016, 2020), inds=None, loo=True):
    """シェア（基準年）×全国の産業別の伸び（自分を除く）＝バーティク"""
    inds = inds or {k: [k] for k in K}
    d = d.copy()
    S = pd.DataFrame({g: d[[f"{k}_{base}" for k in ks]].sum(1) for g, ks in inds.items()})
    T = pd.DataFrame({g: d[[f"{k}_{end}" for k in ks]].sum(1) for g, ks in inds.items()})
    sh = S.div(S.sum(1), axis=0)
    N0, N1 = S.sum(), T.sum()
    if loo:
        g = ((N1 - T).values - (N0 - S).values) / (N0 - S).values      # 自分を除いた全国の伸び
    else:
        g = np.tile(((N1 - N0) / N0).values, (len(d), 1))
    d["bartik"] = (sh.values * g).sum(1) * 100
    d["empg"] = wins((T.sum(1) - S.sum(1)) / S.sum(1) * 100)
    popb = d["pop2015"] if mig[0] >= 2015 else d["pop2010"]
    d["netmig"] = wins(d[[f"net{y}" for y in range(mig[0], mig[1] + 1)]].sum(1) / popb * 100)
    d["lpop"] = np.log(d["pop2015"])
    d["popw"] = d["pop2015"]
    nat_g = (N1.sum() - N0.sum()) / N0.sum()
    return d, sh, ((N1 - N0) / N0), nat_g

CTRL = ["lpop", "old15", "work15"]

def fit(d, fe=True, weights=None, ctrl=CTRL):
    X = d[ctrl].copy()
    if fe:
        X = pd.concat([X, pd.get_dummies(d["pref"], prefix="p", drop_first=True, dtype=float)], axis=1)
    X = sm.add_constant(X)
    w = d[weights] if weights else None
    ols = IV2SLS(d["netmig"], pd.concat([X, d[["empg"]]], axis=1), None, None, weights=w).fit(cov_type="clustered", clusters=d["pref"])
    iv = IV2SLS(d["netmig"], X, d[["empg"]], d[["bartik"]], weights=w).fit(cov_type="clustered", clusters=d["pref"])
    fs = IV2SLS(d["empg"], pd.concat([X, d[["bartik"]]], axis=1), None, None, weights=w).fit(cov_type="clustered", clusters=d["pref"])
    rf = IV2SLS(d["netmig"], pd.concat([X, d[["bartik"]]], axis=1), None, None, weights=w).fit(cov_type="clustered", clusters=d["pref"])
    F = (fs.params["bartik"] / fs.std_errors["bartik"]) ** 2
    # Anderson–Rubin の95%区間（β を格子で探す）
    grid = np.linspace(-1.5, 1.5, 151); acc = []
    for b in grid:
        yy = d["netmig"] - b * d["empg"]
        r = IV2SLS(yy, pd.concat([X, d[["bartik"]]], axis=1), None, None, weights=w).fit(cov_type="clustered", clusters=d["pref"])
        if abs(r.params["bartik"] / r.std_errors["bartik"]) < 1.96: acc.append(b)
    ar = (min(acc), max(acc)) if acc else (np.nan, np.nan)
    if acc and (min(acc) <= grid[0] or max(acc) >= grid[-1]): ar = (min(acc), max(acc), "端まで")
    def ci(r, v): return [float(r.params[v]), float(r.conf_int().loc[v, "lower"]), float(r.conf_int().loc[v, "upper"])]
    return dict(ols=ci(ols, "empg"), iv=ci(iv, "empg"), fs=ci(fs, "bartik"), rf=ci(rf, "bartik"),
                F=float(F), ar=[float(x) if not isinstance(x, str) else x for x in ar], n=int(len(d)))

out = {}
d, sh, gk, natg = build(df)
d = d.dropna(subset=["bartik", "empg", "netmig"] + CTRL)
print("N", len(d), "national emp growth 2016-21 %.2f%%" % (natg * 100))
gk.rename(lambda k: IND[k]).mul(100).round(2).to_csv(RES / "industry_growth_2016_2021.csv", encoding="utf-8")
d[["name", "pref", "bartik", "empg", "netmig", "pop2015"]].to_csv(RES / "municipal_analysis_2016_2021.csv", encoding="utf-8")
out["desc"] = {"n": len(d), "nat_growth_pct": natg * 100,
               "bartik_sd": d.bartik.std(), "empg_sd": d.empg.std(), "netmig_mean": d.netmig.mean(), "netmig_sd": d.netmig.std(),
               "corr_bartik_empg": d[["bartik", "empg"]].corr().iloc[0, 1]}
out["main_fe"] = fit(d, fe=True)
out["main_nofe"] = fit(d, fe=False)
print(json.dumps(out, ensure_ascii=False, indent=1))

# Rotemberg 重み（Goldsmith-Pinkham, Sorkin, Swift 2020）：FE＋統制で残差化してから計算
X = sm.add_constant(pd.concat([d[CTRL], pd.get_dummies(d["pref"], drop_first=True, dtype=float)], axis=1))
def resid(v): return v - X @ np.linalg.lstsq(X.values, v.values, rcond=None)[0]
xr, yr = resid(d["empg"]), resid(d["netmig"])
S = sh.loc[d.index]
num = []; betak = []
for k in K:
    s = resid(S[k])
    num.append(gk[k] * 100 * (s @ xr)); betak.append((s @ yr) / (s @ xr) if abs(s @ xr) > 1e-9 else np.nan)
num = np.array(num); alpha = num / num.sum()
rot = pd.DataFrame({"industry": [IND[k] for k in K], "g_pct": (gk * 100).values, "alpha": alpha, "beta_k": betak,
                    "share_mean": S.mean().values})
rot = rot.sort_values("alpha", ascending=False)
rot.to_csv(RES / "rotemberg.csv", index=False, encoding="utf-8")
out["rotemberg_top"] = rot.head(5)[["industry", "alpha", "beta_k", "g_pct"]].round(3).values.tolist()
out["rotemberg_negsum"] = float(alpha[alpha < 0].sum())
print(rot.round(3))

# 頑健性
rob = {}
def run(name, **kw):
    fe = kw.pop("fe", True); wgt = kw.pop("weights", None); sub = kw.pop("subset", None)
    dd, *_ = build(df, **kw); dd = dd.dropna(subset=["bartik", "empg", "netmig"] + CTRL)
    if sub is not None: dd = dd[sub(dd)]
    r = fit(dd, fe=fe, weights=wgt); rob[name] = r
    print(name, {k: (np.round(v, 3) if not isinstance(v, (int, float)) else round(v, 3)) for k, v in r.items() if k in ("iv", "ols", "F", "n")})
run("基本（2016→21、転入超過2016〜20、県FE）")
run("県FEなし", fe=False)
run("人口で重みづけ", weights="popw")
run("東京圏（1都3県）を除く", subset=lambda x: ~x.pref.isin(["11", "12", "13", "14"]))
run("転入超過を2017〜21に", mig=(2017, 2021))
run("基準年を2014に（シェア2014、伸び2014→21）", base=2014, end=2021, mig=(2014, 2020))
GROUPS = {"一次・鉱業": ["C220832", "C220833", "C220835"], "建設": ["C220836"], "製造": ["C220837"],
          "インフラ・運輸・情報": ["C220838", "C220839", "C220840"], "商業・金融・不動産": ["C220841", "C220844", "C220845"],
          "対個人サービス": ["C220847", "C220848", "C220849"], "医療・福祉": ["C220850"],
          "その他サービス": ["C220846", "C220851", "C220852"]}
run("産業を8分類にまとめる", inds=GROUPS)
run("自分を除かない全国の伸び", loo=False)
run("人口1万人以上", subset=lambda x: x.pop2015 >= 10000)
out["robust"] = rob

# 事前トレンド（プラセボ）：2016→21 のバーティクで、それより前の転入超過を説明できてしまうか
pre = {}
for nm, (a, b) in {"2010〜14の転入超過": (2010, 2014), "2011〜15の転入超過": (2011, 2015)}.items():
    dd, *_ = build(df, mig=(a, b)); dd = dd.dropna(subset=["bartik", "netmig"] + CTRL)
    X = sm.add_constant(pd.concat([dd[CTRL], pd.get_dummies(dd["pref"], drop_first=True, dtype=float), dd[["bartik"]]], axis=1))
    r = IV2SLS(dd["netmig"], X, None, None).fit(cov_type="clustered", clusters=dd["pref"])
    pre[nm] = [float(r.params["bartik"]), *r.conf_int().loc["bartik"].astype(float).tolist()]
# 本期の誘導形と並べる
dd, *_ = build(df); dd = dd.dropna(subset=["bartik", "netmig"] + CTRL)
pre["2016〜20の転入超過（本期）"] = out["main_fe"]["rf"]
# 前期の転入超過を統制しても変わるか
dd["netpre"] = dd[[f"net{y}" for y in range(2011, 2016)]].sum(1) / dd["pop2010"] * 100
r = fit(dd, fe=True, ctrl=CTRL + ["netpre"]); rob["前期（2011〜15）の転入超過を統制"] = r
out["pretrend"] = pre
print("pretrend", pre)

# 期間を変えた推定：2014→16（短期）
dd, *_ = build(df, base=2014, end=2016, mig=(2014, 2016)); dd = dd.dropna(subset=["bartik", "empg", "netmig"] + CTRL)
rob["期間 2014→16（基礎調査→活動調査）"] = fit(dd, fe=True)

# 都道府県単位の参考（F33 の都道府県間移動、47）
pp = pd.read_csv(DATA / "raw" / "f33_pref_migration_panel.csv")
pp = pp[(pp.year >= 2016) & (pp.year <= 2020)]
inn = pp.groupby("d").flow.sum(); outf = pp.groupby("o").flow.sum()
pr = df.copy(); pr["pref_i"] = pr.pref.astype(int)
agg = pr.groupby("pref_i")[[f"{k}_{y}" for k in K for y in (2016, 2021)] + ["pop2015", "pop2020"]].sum()
S = agg[[f"{k}_2016" for k in K]].values; T = agg[[f"{k}_2021" for k in K]].values
sh47 = S / S.sum(1, keepdims=True); N0, N1 = S.sum(0), T.sum(0)
g47 = ((N1 - T) - (N0 - S)) / (N0 - S)
agg["bartik"] = (sh47 * g47).sum(1) * 100
agg["empg"] = (T.sum(1) - S.sum(1)) / S.sum(1) * 100
agg["netmig"] = (inn - outf).reindex(agg.index) / agg["pop2015"] * 100
agg["const"] = 1.0
o = IV2SLS(agg["netmig"], agg[["const", "empg"]], None, None).fit(cov_type="robust")
iv = IV2SLS(agg["netmig"], agg[["const"]], agg[["empg"]], agg[["bartik"]]).fit(cov_type="robust")
fs = IV2SLS(agg["empg"], agg[["const", "bartik"]], None, None).fit(cov_type="robust")
out["pref47"] = {"ols": [float(o.params.empg), *o.conf_int().loc["empg"].astype(float).tolist()],
                 "iv": [float(iv.params.empg), *iv.conf_int().loc["empg"].astype(float).tolist()],
                 "F": float((fs.params.bartik / fs.std_errors.bartik) ** 2)}
agg[["bartik", "empg", "netmig"]].to_csv(RES / "pref47.csv", encoding="utf-8")
print("pref47", out["pref47"])

json.dump(out, open(RES / "results.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
rows = []
for k, v in rob.items():
    rows.append([k, v["n"], *np.round(v["ols"], 3), *np.round(v["iv"], 3), round(v["F"], 1)])
pd.DataFrame(rows, columns=["設定", "N", "OLS", "OLS下", "OLS上", "IV", "IV下", "IV上", "第1段階F"]).to_csv(RES / "robustness.csv", index=False, encoding="utf-8")

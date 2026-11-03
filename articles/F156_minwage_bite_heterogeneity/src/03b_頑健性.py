"""(A) の交互作用の頑健性：固定効果の入れ方・期間・地域の除外と、引き上げの年の並べ替え（プラセボ）"""
import json, warnings
import numpy as np, pandas as pd, statsmodels.formula.api as smf
from common import DATA, RES, SEED
warnings.filterwarnings("ignore")
rng = np.random.default_rng(SEED)
w = pd.read_csv(DATA / "panel_wage.csv"); e = pd.read_csv(DATA / "panel_emp.csv")
for d in (w, e):
    d["low_wage"] = -(d.wage0 - d.wage0.mean()) / d.wage0.std()
    d["bite"] = (d.bite0 - d.bite0.mean()) / d.bite0.std()
    d["low_mw"] = -(d.lmw0 - d.lmw0.mean()) / d.lmw0.std()
TOHOKU3 = [3, 4, 7]
SAMPLES = {
    "wage": {"基本（2012〜19年）": w[w.year.between(2012, 2019)],
             "2021〜25年も含める（2020年の断絶は除く）": w[w.year.between(2012, 2019) | w.year.between(2021, 2025)],
             "2015〜19年だけ": w[w.year.between(2015, 2019)]},
    "emp": {"基本（2012〜19・23〜25年）": e[e.year.between(2012, 2019) | e.year.between(2023, 2025)],
            "2012〜19年だけ": e[e.year.between(2012, 2019)],
            "2020〜22年も含める": e[e.year.between(2012, 2025)]},
}
SAMPLES["unemp"] = SAMPLES["emp"]
Y = {"wage": "dlw", "emp": "d_emp", "unemp": "d_unemp"}

def est(y, d, mod, fe="C(year)", extra=""):
    d = d.dropna(subset=[y, "lag_d_emp"] if y != "dlw" else [y])
    f = f"{y} ~ dlmw + dlmw:{mod} + {mod} + {fe}{extra}"
    m = smf.ols(f, d).fit(cov_type="cluster", cov_kwds={"groups": d["code"]})
    k = f"dlmw:{mod}"
    return m.params[k], m.bse[k], m.pvalues[k]

rows = []
for o, y in Y.items():
    ex = " + lag_d_emp" if o != "wage" else ""
    for mod in ["low_wage", "bite", "low_mw"]:
        for sn, d in SAMPLES[o].items():
            b, se, p = est(y, d, mod, extra=ex); rows.append(dict(outcome=o, mod=mod, spec=sn, b=b, se=se, p=p))
        d0 = list(SAMPLES[o].values())[0]
        for sn, fe, dd in [("県ごとの傾き（県の固定効果）", "C(year) + C(code)", d0),
                           ("地方×年の効果（同じ地方の中だけで比べる）", "C(year):C(region)", d0),
                           ("東北3県（岩手・宮城・福島）を除く", "C(year)", d0[~d0.code.isin(TOHOKU3)])]:
            b, se, p = est(y, dd, mod, fe=fe, extra=ex); rows.append(dict(outcome=o, mod=mod, spec=sn, b=b, se=se, p=p))
rob = pd.DataFrame(rows)

# プラセボ：全国の引き上げの「年」を並べ替える。県ごとのずれ（年平均からの差）はそのまま
perm = []; tdraws = []
for o, y in Y.items():
    ex = " + lag_d_emp" if o != "wage" else ""
    d0 = list(SAMPLES[o].values())[0].dropna(subset=[y] + (["lag_d_emp"] if o != "wage" else [])).copy()
    yrs = np.sort(d0.year.unique())
    ym = d0.groupby("year").dlmw.mean()
    dev = d0.dlmw - d0.year.map(ym)
    for mod in ["low_wage", "bite", "low_mw"]:
        b0, se0, _ = est(y, d0, mod, extra=ex)
        t0 = b0 / se0
        ts = []
        for i in range(300):
            mp = dict(zip(yrs, rng.permutation(ym.loc[yrs].values)))
            dd = d0.copy(); dd["dlmw"] = dd.year.map(mp) + dev
            b, se, _ = est(y, dd, mod, extra=ex); ts.append(b / se)
        ts = np.array(ts); tdraws += [dict(outcome=o, mod=mod, t=t) for t in ts]
        perm.append(dict(outcome=o, mod=mod, t_obs=t0, p_perm=float(np.mean(np.abs(ts) >= abs(t0))), t_perm_sd=float(ts.std())))
perm = pd.DataFrame(perm)
rob.round(5).to_csv(RES / "robustness.csv", index=False)
perm.round(4).to_csv(RES / "placebo_year_permutation.csv", index=False)
pd.DataFrame(tdraws).round(4).to_csv(RES / "placebo_t_draws.csv", index=False)
pd.set_option("display.width", 220); pd.set_option("display.max_rows", 200)
print(rob.round(3).to_string()); print(perm.round(3))

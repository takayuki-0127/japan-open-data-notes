"""PLAN の仮説 H1〜H5 と頑健性を計算し、results/ に書く。"""
import json, os
import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.api as sm

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
RES = os.path.join(HERE, "..", "results")
os.makedirs(RES, exist_ok=True)

s = pd.read_csv(os.path.join(DATA, "season.csv"), index_col=0)
st = pd.read_csv(os.path.join(DATA, "stations.csv"))
ab = st[st.station == "abashiri"].set_index("season")
r1 = lambda x: float(round(float(x), 1))
r2 = lambda x: float(round(float(x), 2))
r3 = lambda x: float(round(float(x), 3))


def ts(y):
    """Theil–Sen の傾き（1年あたり）と95%区間、Mann–Kendall の p。"""
    y = y.dropna()
    x = y.index.values.astype(float)
    sl, ic, lo, hi = stats.theilslopes(y.values, x)
    tau = stats.kendalltau(x, y.values)
    return {"slope": sl, "lo": lo, "hi": hi, "n": int(len(y)), "first": int(x.min()), "last": int(x.max()),
            "mk_tau": tau.statistic, "mk_p": tau.pvalue, "intercept": ic}


def ols(y):
    y = y.dropna()
    X = sm.add_constant(y.index.values.astype(float))
    m = sm.OLS(y.values, X).fit(cov_type="HAC", cov_kwds={"maxlags": 3})
    return {"slope": m.params[1], "se_hac": m.bse[1], "p_hac": m.pvalues[1]}


def rel(var, d, base=(1971, 2000)):
    """10年あたりの傾きを、基準期間の平均に対する%で。"""
    b = d[var].loc[base[0]:base[1]].mean()
    t = ts(d[var])
    return {"pct_per_decade": t["slope"] * 10 / b * 100, "abs_per_decade": t["slope"] * 10, "base_mean": b,
            "lo_pct": t["lo"] * 10 / b * 100, "hi_pct": t["hi"] * 10 / b * 100, "mk_p": t["mk_p"], "n": t["n"]}


def pack(d):
    return {k: (r3(v) if isinstance(v, float) else v) for k, v in d.items()}


R = {}
# ---- 確かめ：最大海氷域面積（気象庁の値は最小二乗法で 10年あたり −5.9万km²）
mx = ts(s["max_official"]); mo = ols(s["max_official"])
R["check_max"] = {"theil_sen_per_decade": r2(mx["slope"] * 10), "ols_per_decade": r2(mo["slope"] * 10),
                  "ols_hac_se_per_decade": r2(mo["se_hac"] * 10), "n": mx["n"],
                  "mean_1971_2000": r1(s["max_official"].loc[1971:2000].mean()),
                  "mean_1997_2026": r1(s["max_official"].loc[1997:2026].mean()),
                  "okhotsk_area_note": "気象庁はオホーツク海の全面積に対する割合で 10年あたり3.7% と説明"}

# ---- H1：積算と最大の減り方（%/10年）
base = (1972, 2000)  # 積算は1971年に12月の値がないので1972年から
h1_acc = rel("acc_dec_may", s, base)
h1_max = rel("max_dec_may", s.loc[1972:], base)
R["H1"] = {"acc": pack(h1_acc), "max": pack(h1_max), "base_years": list(base),
           "result": "支持" if h1_acc["pct_per_decade"] < h1_max["pct_per_decade"] else "外れ"}

# ---- H2：4〜5月と2〜3月
h2_am = rel("mean_apr_may", s, base); h2_fm = rel("mean_feb_mar", s, base); h2_dj = rel("mean_dec_jan", s, base)
R["H2"] = {"apr_may": pack(h2_am), "feb_mar": pack(h2_fm), "dec_jan_ref": pack(h2_dj), "base_years": list(base),
           "result": "支持" if h2_am["pct_per_decade"] < h2_fm["pct_per_decade"] else "外れ"}

# ---- H3・H4：網走の初日・終日
f = ts(ab["first"]); l = ts(ab["last"]); pr = ts(ab["period"]); sh = ts(ab["shore_first"]); op = ts(ab["sea_open"])
R["H3"] = {"slope_days_per_decade": r2(f["slope"] * 10), "lo": r2(f["lo"] * 10), "hi": r2(f["hi"] * 10),
           "mk_p": r3(f["mk_p"]), "n": f["n"], "years": [f["first"], f["last"]],
           "mean_1946_1975": r1(ab["first"].loc[1946:1975].mean()), "mean_1996_2025": r1(ab["first"].loc[1996:2025].mean()),
           "result": "支持" if f["slope"] * 10 >= 1.0 else "外れ"}
R["H4"] = {"slope_days_per_decade": r2(l["slope"] * 10), "lo": r2(l["lo"] * 10), "hi": r2(l["hi"] * 10),
           "mk_p": r3(l["mk_p"]), "n": l["n"], "years": [l["first"], l["last"]],
           "mean_1946_1975": r1(ab["last"].loc[1946:1975].mean()), "mean_1992_2021": r1(ab["last"].loc[1992:2021].mean()),
           "result": "支持" if l["slope"] * 10 <= -1.0 else "外れ",
           "period_slope_per_decade": r2(pr["slope"] * 10), "period_mk_p": r3(pr["mk_p"]),
           "period_mean_1946_1975": r1(ab["period"].loc[1946:1975].mean()),
           "period_mean_1992_2021": r1(ab["period"].loc[1992:2021].mean()),
           "sea_open_slope_per_decade": r2(op["slope"] * 10), "sea_open_mk_p": r3(op["mk_p"]), "sea_open_n": op["n"]}

# ---- H5：気温との相関（傾きを除いた残り）
def detrended_corr(yname, tname, d):
    z = d[[yname, tname]].dropna()
    x = z.index.values.astype(float)
    res = {}
    for c in (yname, tname):
        b = np.polyfit(x, z[c].values, 1)
        res[c] = z[c].values - np.polyval(b, x)
    r = stats.pearsonr(res[yname], res[tname])
    raw = stats.pearsonr(z[yname], z[tname])
    # 1℃あたりの面積の変化（残りどうしの回帰）
    sl = stats.linregress(res[tname], res[yname]).slope
    return {"r_detrended": r3(r.statistic), "p": float(f"{r.pvalue:.2e}"), "r_raw": r3(raw.statistic),
            "n": int(len(z)), "slope_per_degC": r1(sl)}

h5 = detrended_corr("acc_dec_may", "t_jan_mar", s)
R["H5"] = {**h5, "result": "支持" if h5["r_detrended"] <= -0.5 else "外れ",
           "robust_t_dec_feb": detrended_corr("acc_dec_may", "t_dec_feb", s),
           "robust_t_feb_mar": detrended_corr("acc_dec_may", "t_feb_mar", s),
           "robust_max_vs_jan_mar": detrended_corr("max_dec_may", "t_jan_mar", s)}
tt = ts(s["t_jan_mar"].loc[1972:2026])
R["temp"] = {"t_jan_mar_slope_per_decade_1972_2026": r2(tt["slope"] * 10),
             "t_jan_mar_mean_1972_2000": r1(s["t_jan_mar"].loc[1972:2000].mean()),
             "t_jan_mar_mean_1997_2026": r1(s["t_jan_mar"].loc[1997:2026].mean())}
# 気温の上昇だけで説明できる積算の減り（1℃あたりの関係 × 気温の傾き）を、実際の傾きと比べる（推測の目安）
acc_ts = ts(s["acc_dec_may"])
R["temp_share"] = {"acc_slope_per_decade": r1(acc_ts["slope"] * 10),
                   "implied_by_temp_per_decade": r1(h5["slope_per_degC"] * tt["slope"] * 10)}

# ---- 頑健性の表
rob = []
def add(label, var, d, base_=base):
    r = rel(var, d, base_)
    o = ols(d[var])
    rob.append({"check": label, "var": var, "first": int(d[var].dropna().index.min()), "last": int(d[var].dropna().index.max()),
                "theil_sen_pct_per_decade": r2(r["pct_per_decade"]), "ols_pct_per_decade": r2(o["slope"] * 10 / r["base_mean"] * 100),
                "ols_hac_p": r3(o["p_hac"]), "mk_p": r3(r["mk_p"])})
add("本線", "acc_dec_may", s)
add("本線", "max_dec_may", s.loc[1972:])
add("本線", "mean_apr_may", s)
add("本線", "mean_feb_mar", s)
add("1981年以降", "acc_dec_may", s.loc[1981:])
add("1981年以降", "max_dec_may", s.loc[1981:])
add("1981年以降", "mean_apr_may", s.loc[1981:])
add("1981年以降", "mean_feb_mar", s.loc[1981:])
add("積算を1〜4月に", "acc_jan_apr", s)
rb = pd.DataFrame(rob)
rb.to_csv(os.path.join(RES, "robustness_area.csv"), index=False)

rd = []
for lab, col, d in [("流氷初日", "first", ab), ("流氷接岸初日", "shore_first", ab), ("流氷終日", "last", ab),
                    ("流氷期間", "period", ab), ("海明け", "sea_open", ab)]:
    for per, dd in (("全期間", d), ("1981年以降", d.loc[1981:])):
        t = ts(dd[col]); o = ols(dd[col])
        rd.append({"item": lab, "period": per, "n": t["n"], "first": t["first"], "last": t["last"],
                   "theil_sen_days_per_decade": r2(t["slope"] * 10), "ols_days_per_decade": r2(o["slope"] * 10),
                   "ols_hac_p": r3(o["p_hac"]), "mk_p": r3(t["mk_p"])})
pd.DataFrame(rd).to_csv(os.path.join(RES, "robustness_abashiri.csv"), index=False)
R["H3"]["robust_shore_first_per_decade"] = r2(ts(ab["shore_first"])["slope"] * 10)
R["H3"]["robust_shore_first_mk_p"] = r3(ts(ab["shore_first"])["mk_p"])

# 季節の形：1972〜2000年と1997〜2026年の半旬ごとの平均
raw = open(os.path.join(DATA, "raw", "okhotsk_alldata.txt"), encoding="utf-8").read().splitlines()
cols = raw[1].split()[1:]
rows = [[int(t[0][:4]) + 1] + [float(v) for v in t[1:]] for t in (ln.split() for ln in raw[2:]) if len(t) == len(cols) + 1]
a = pd.DataFrame(rows, columns=["season"] + cols).set_index("season").replace(-99.99, np.nan)
dm = [c for c in cols if c[:2] in ("12", "01", "02", "03", "04", "05")]
clim = pd.DataFrame({"pentad": dm, "mean_1972_2000": a.loc[1972:2000, dm].mean().values,
                     "mean_1997_2026": a.loc[1997:2026, dm].mean().values})
clim["change_pct"] = (clim["mean_1997_2026"] / clim["mean_1972_2000"] - 1) * 100
clim.round(2).to_csv(os.path.join(RES, "pentad_climatology.csv"), index=False)
R["pentad"] = {"largest_drop_pentad": clim.loc[clim["change_pct"].idxmin(), "pentad"],
               "largest_drop_pct": r1(clim["change_pct"].min()),
               "smallest_drop_pentad": clim.loc[clim["change_pct"].idxmax(), "pentad"],
               "smallest_drop_pct": r1(clim["change_pct"].max())}

s.round(3).to_csv(os.path.join(RES, "season_table.csv"))
with open(os.path.join(RES, "main.json"), "w", encoding="utf-8") as fo:
    json.dump(R, fo, ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps(R, ensure_ascii=False, indent=1))
print(rb.to_string()); print(pd.DataFrame(rd).to_string())

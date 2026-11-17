"""節電要請の期間の需要が、気温・曜日・月・年度で見込まれる値よりどれだけ低いか。仮説・頑健性。結果は results/ に出す。"""
import json, pathlib
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; R.mkdir(exist_ok=True)
d = pd.read_csv(ROOT / "data" / "daily.csv", parse_dates=["date"]).set_index("date").sort_index()
d["temp"] = (d.temp_fukuoka + d.temp_kagoshima) / 2
d["ln_d"] = np.log(d.demand_gwh); d["ln_e"] = np.log(d.evening_gwh)
d["daytype"] = np.where(d.holiday == 1, "hol", d.dow.astype(str))
d["summer22"] = ((d.index >= "2022-07-01") & (d.index <= "2022-09-30")).astype(int)
d["winter22"] = ((d.index >= "2022-12-01") & (d.index <= "2023-03-31")).astype(int)
d["summer23"] = ((d.index >= "2023-07-01") & (d.index <= "2023-09-30")).astype(int)   # プラセボ（要請なし）
d["winter23"] = ((d.index >= "2023-12-01") & (d.index <= "2024-03-31")).astype(int)


def tbin(t):
    return np.clip(np.floor(t), -2, 31).astype(int).astype(str)


def fit(df, y="ln_d", temp="temp", fe="C(fy)", placebo=False, quad=False):
    df = df.copy()
    df["tb"] = tbin(df[temp])
    df["t1"] = df[temp]; df["t2"] = df[temp] ** 2
    tt = "t1 + t2 + I(t1**3)" if quad else "C(tb)"
    ev = "summer22 + winter22" + (" + summer23 + winter23" if placebo else "")
    f = smf.ols(f"{y} ~ {ev} + {tt} + C(daytype) + C(month) + {fe}", df).fit(cov_type="HAC", cov_kwds={"maxlags": 7})
    out = {}
    for k in (["summer22", "winter22"] + (["summer23", "winter23"] if placebo else [])):
        b, se = f.params[k], f.bse[k]
        out[k] = {"pct": round(float((np.exp(b) - 1) * 100), 2), "lo": round(float((np.exp(b - 1.96 * se) - 1) * 100), 2),
                  "hi": round(float((np.exp(b + 1.96 * se) - 1) * 100), 2)}
    out["r2"] = round(float(f.rsquared), 4); out["n"] = int(f.nobs)
    return out, f


base, fb = fit(d)
eve, _ = fit(d, y="ln_e")
plc, _ = fit(d, placebo=True)
# 見込みと実際（図用）：要請のダミーを0にした予測
X = d.copy(); X["tb"] = tbin(X.temp); X["t1"] = X.temp; X["t2"] = X.temp ** 2
X0 = X.copy(); X0["summer22"] = 0; X0["winter22"] = 0
d["pred_no_request_gwh"] = np.exp(fb.predict(X0))
d["resid_pct"] = (d.demand_gwh / d.pred_no_request_gwh - 1) * 100
d[["demand_gwh", "evening_gwh", "temp", "pred_no_request_gwh", "resid_pct", "summer22", "winter22"]].round(4).to_csv(R / "daily_fit.csv")

rob = []
for name, kw, df in [("本線：気温は福岡・鹿児島の平均（1℃刻み）、年度の固定効果", {}, d),
                     ("気温は福岡だけ", {"temp": "temp_fukuoka"}, d),
                     ("2020年度を除く", {}, d[d.fy != 2020]),
                     ("平日だけ（祝日・年末年始を除く月〜金）", {}, d[(d.dow < 5) & (d.holiday == 0)]),
                     ("気温は3次の式", {"quad": True}, d),
                     ("年度の固定効果の代わりに直線の傾き", {"fe": "trend"}, d.assign(trend=(d.index - d.index[0]).days / 365.25))]:
    o, _ = fit(df, **kw)
    rob.append({"check": name, "summer_pct": o["summer22"]["pct"], "summer_lo": o["summer22"]["lo"], "summer_hi": o["summer22"]["hi"],
                "winter_pct": o["winter22"]["pct"], "winter_lo": o["winter22"]["lo"], "winter_hi": o["winter22"]["hi"], "n": o["n"]})
rob = pd.DataFrame(rob)
rob.to_csv(R / "robustness.csv", index=False)

s, w = base["summer22"]["pct"], base["winter22"]["pct"]
main = {
    "n_days": base["n"], "r2": base["r2"],
    "summer22": base["summer22"], "winter22": base["winter22"],
    "evening_summer22": eve["summer22"], "evening_winter22": eve["winter22"],
    "placebo_summer23": plc["summer23"], "placebo_winter23": plc["winter23"],
    "placebo_model_summer22": plc["summer22"], "placebo_model_winter22": plc["winter22"],
    "mean_daily_gwh_summer22": round(float(d[d.summer22 == 1].demand_gwh.mean()), 1),
    "mean_daily_gwh_winter22": round(float(d[d.winter22 == 1].demand_gwh.mean()), 1),
    "hypotheses": {
        "H1_summer_le_minus1": {"value": s, "result": "支持" if s <= -1 else "外れ"},
        "H2_winter_le_minus1": {"value": w, "result": "支持" if w <= -1 else "外れ"},
        "H3_evening_bigger": {"summer": [eve["summer22"]["pct"], s], "winter": [eve["winter22"]["pct"], w],
                              "result": "支持" if (eve["summer22"]["pct"] < s and eve["winter22"]["pct"] < w) else ("一部支持" if (eve["summer22"]["pct"] < s or eve["winter22"]["pct"] < w) else "外れ")},
        "H4_placebo_within_1": {"summer23": plc["summer23"]["pct"], "winter23": plc["winter23"]["pct"],
                                "result": "支持" if (abs(plc["summer23"]["pct"]) <= 1 and abs(plc["winter23"]["pct"]) <= 1) else "外れ"},
    },
}
json.dump(main, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(main, ensure_ascii=False, indent=1)); print(rob.to_string())

"""F277 02 整形：年度ごとの表（2003〜2026）を作る → data/processed/panel.csv"""
import os, json
import pandas as pd, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "..", "data", "raw"); OUT = os.path.join(HERE, "..", "data", "processed")
os.makedirs(OUT, exist_ok=True)
mw = pd.read_csv(os.path.join(RAW, "jil_mw_weighted_avg.csv")).set_index("fy")["mw_hourly"]
t4 = pd.read_csv(os.path.join(RAW, "t4_rate.csv")).set_index("year")["t4"]
spr = pd.read_csv(os.path.join(RAW, "jil_springwage.csv")).set_index("year")["spring_rate"]
cpi = pd.read_csv(os.path.join(RAW, "cpi_ex_imputed_rent_monthly.csv"), dtype={"ym": str})
cpi["date"] = pd.to_datetime(cpi["ym"], format="%Y%m")
s = cpi.set_index("date")["cpi_ex_imputed_rent"].astype(float)
yoy = (s / s.shift(12) - 1) * 100
ann = s.groupby(s.index.year).mean()
j = json.load(open(os.path.join(RAW, "boj_tankan_sme.json"), encoding="utf-8"))
tk = {}
for r in j["RESULTSET"]:
    key = "di_biz" if "業況" in r["NAME_OF_TIME_SERIES_J"] else "di_emp"
    for d, v in zip(r["VALUES"]["SURVEY_DATES"], r["VALUES"]["VALUES"]):
        if v is not None and str(d).endswith("02"):   # 6月調査
            tk.setdefault(int(str(d)[:4]), {})[key] = v
addon = pd.read_csv(os.path.join(RAW, "mw_add_on_over_meyasu_2016_2025.csv")).set_index("pref")
rows = []
for t in range(2003, 2027):
    w = yoy[(yoy.index >= f"{t-1}-10-01") & (yoy.index <= f"{t}-06-01")]
    assert len(w) == 9
    r = dict(year=t,
             mw=mw[t], mw_prev=mw[t - 1],
             y=(mw[t] / mw[t - 1] - 1) * 100, y_yen=mw[t] - mw[t - 1],
             t4=t4[t], cpi=w.mean(), cpi_cal=(ann[t - 1] / ann[t - 2] - 1) * 100,
             spr=spr[t], di_biz=tk[t]["di_biz"], di_emp=tk[t]["di_emp"],
             addon_mean=addon[f"fy{t}"].mean() if f"fy{t}" in addon else np.nan)
    r["y_prev"] = (mw[t - 1] / mw[t - 2] - 1) * 100 if t - 2 in mw.index else np.nan
    rows.append(r)
p = pd.DataFrame(rows)
p["y_meyasu_approx"] = (p["mw"] - p["addon_mean"] - p["mw_prev"]) / p["mw_prev"] * 100
p.to_csv(os.path.join(OUT, "panel.csv"), index=False, float_format="%.4f")
print(p.round(2).to_string())

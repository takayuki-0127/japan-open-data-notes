"""問い直し（結果を見てから足した）：態度指数が消費を先取りしないなら、態度指数は何と一緒に動いているのか。
物価の上がり方（消費者物価指数 持家の帰属家賃を除く総合の前年同月比）と、消費（家計調査の実質増減率）を並べる。ネットにはつながない。"""
import json, sys, pathlib
import numpy as np
import pandas as pd
import statsmodels.api as sm

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import RES, DATA, ROOT

raw = pd.read_csv(ROOT / "data" / "raw" / "cpi_2025base_middle_class_monthly.csv", encoding="cp932", header=None, dtype=str)
hdr = list(raw.iloc[0])
col = hdr.index("持家の帰属家賃を除く総合")
r = raw[raw[0].str.match(r"^\d{6}$", na=False)]
cpi = pd.DataFrame({"year": r[0].str[:4].astype(int), "month": r[0].str[4:].astype(int), "cpi": r[col].astype(float)})
cpi = cpi.sort_values(["year", "month"]).reset_index(drop=True)
cpi["infl"] = 100 * (cpi["cpi"] / cpi["cpi"].shift(12) - 1)
cpi[["year", "month", "cpi", "infl"]].to_csv(DATA / "cpi_monthly.csv", index=False, float_format="%.4f")

c = pd.read_csv(DATA / "cci_monthly.csv")
k = pd.read_csv(DATA / "kakei_monthly.csv")
m = c.merge(cpi, on=["year", "month"], how="left").merge(k[["year", "month", "cons"]], on=["year", "month"], how="left")
m = m[(m.year > 2004) | ((m.year == 2004) & (m.month >= 4))].sort_values(["year", "month"]).reset_index(drop=True)
m.to_csv(RES / "requestion_monthly.csv", index=False, float_format="%.4f")

out = {}
for name, sub in [("all", m), ("2005_2019", m[(m.year >= 2005) & (m.year <= 2019)]), ("2021_2026", m[m.year >= 2021])]:
    z = sub.dropna(subset=["cci", "infl", "cons"])
    res = sm.OLS(z["cci"], sm.add_constant(z[["infl", "cons"]])).fit(cov_type="HAC", cov_kwds={"maxlags": 12})
    out[name] = {"n": int(len(z)), "period": f"{int(z.year.iloc[0])}-{int(z.month.iloc[0]):02d}〜{int(z.year.iloc[-1])}-{int(z.month.iloc[-1]):02d}",
                 "r_cci_infl": round(float(np.corrcoef(z.cci, z.infl)[0, 1]), 4),
                 "r_cci_cons": round(float(np.corrcoef(z.cci, z.cons)[0, 1]), 4),
                 "b_infl": round(float(res.params["infl"]), 4), "t_infl": round(float(res.tvalues["infl"]), 4),
                 "b_cons": round(float(res.params["cons"]), 4), "t_cons": round(float(res.tvalues["cons"]), 4),
                 "cci_mean": round(float(z.cci.mean()), 4), "infl_mean": round(float(z.infl.mean()), 4), "cons_mean": round(float(z.cons.mean()), 4)}
# 物価の見方の構成：暮らし向き と 雇用環境 の差（2021年以降と2005〜2019年の平均）
for name, sub in [("2005_2019", m[(m.year >= 2005) & (m.year <= 2019)]), ("2021_2026", m[m.year >= 2021])]:
    for v in ["kurashi", "shunyu", "koyo", "kaidoki"]:
        out[name]["mean_" + v] = round(float(sub[v].mean()), 4)
json.dump(out, open(RES / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps(out, ensure_ascii=False, indent=1))

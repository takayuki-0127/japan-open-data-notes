"""問い直し（結果を見てから足した）：
倍率の高い職業は、もともと賃金が低かったのか。2022年の賃金の水準をそろえると、倍率と伸びの関係はどうなるか。"""
import json, pathlib
import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES = ROOT / "results"
d = pd.read_csv(RES / "group_table.csv").sort_values("group_id").reset_index(drop=True)
d["log_pay_2022"] = np.log(d.scheduled_pay_2022)
d["log_pay_2022_c"] = d.log_pay_2022 - np.average(d.log_pay_2022, weights=d.workers_2022)

def fit(y, xs):
    m = sm.WLS(d[y], sm.add_constant(d[xs]), weights=d.workers_2022).fit(cov_type="HC3")
    return {x: dict(coef=round(float(m.params[x]), 4), se=round(float(m.bse[x]), 4), p=round(float(m.pvalues[x]), 4)) for x in xs} | {"r2": round(float(m.rsquared), 4), "n": int(m.nobs)}

out = {
    "level_on_ratio": fit("log_pay_2022", ["ratio_fy2022_all"]),           # 水準と倍率
    "growth_on_level": fit("g_pay_22_25", ["log_pay_2022_c"]),             # 伸びと水準
    "growth_on_ratio_and_level": fit("g_pay_22_25", ["ratio_fy2022_all", "log_pay_2022_c"]),
}
# 賃金の水準で2つに分けて、それぞれの中で倍率と伸びの傾き
med = np.median(d.log_pay_2022)
for lab, sub in (("low_pay_half", d[d.log_pay_2022 <= med]), ("high_pay_half", d[d.log_pay_2022 > med])):
    m = sm.WLS(sub.g_pay_22_25, sm.add_constant(sub[["ratio_fy2022_all"]]), weights=sub.workers_2022).fit(cov_type="HC3")
    out[lab] = dict(n=int(m.nobs), slope=round(float(m.params["ratio_fy2022_all"]), 4), se=round(float(m.bse["ratio_fy2022_all"]), 4),
                    p=round(float(m.pvalues["ratio_fy2022_all"]), 4),
                    mean_growth=round(float(np.average(sub.g_pay_22_25, weights=sub.workers_2022)), 3),
                    mean_ratio=round(float(np.average(sub.ratio_fy2022_all, weights=sub.workers_2022)), 3))
out["pay_median_2022_thousand_yen"] = round(float(np.exp(med)), 1)
# 1%上の賃金水準 → 伸びが何%pt 違うか を読みやすく：賃金が10%高い職業の伸びの差
out["growth_diff_per_10pct_higher_level"] = round(out["growth_on_level"]["log_pay_2022_c"]["coef"] * np.log(1.1), 3)
(RES / "requestion.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(out, ensure_ascii=False, indent=0))

"""問い直し（結果を見てから足した）：
H3 で倍率の係数は正だったが、2007-09 → 2023-25 の上昇のうち、景気（有効求人倍率）の分で説明できるのはどれくらいか。
同じくらいの倍率の年どうしで比べると、増加の割合はどれだけ違うか。"""
import json, pathlib
import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES = ROOT / "results"
ts = pd.read_csv(RES / "timeseries_all.csv")
m = json.loads((RES / "main.json").read_text(encoding="utf-8"))
r3 = lambda x: round(float(x), 3)
S, E = [2007, 2008, 2009], [2023, 2024, 2025]
d = ts[(ts.year >= 2007)].copy(); d["trend"] = d.year - 2007
fit = sm.OLS(d.up10, sm.add_constant(d[["jobs_ratio", "trend"]])).fit()
b_r, b_t = fit.params["jobs_ratio"], fit.params["trend"]
dr = d[d.year.isin(E)].jobs_ratio.mean() - d[d.year.isin(S)].jobs_ratio.mean()
dt = np.mean(E) - np.mean(S)
obs = d[d.year.isin(E)].up10.mean() - d[d.year.isin(S)].up10.mean()
out = dict(observed_change=r3(obs), jobs_ratio_start=r3(d[d.year.isin(S)].jobs_ratio.mean()), jobs_ratio_end=r3(d[d.year.isin(E)].jobs_ratio.mean()),
           part_jobs_ratio=r3(b_r * dr), part_trend=r3(b_t * dt), residual=r3(obs - b_r * dr - b_t * dt),
           share_jobs_ratio=r3(b_r * dr / obs), share_trend=r3(b_t * dt / obs))
# 倍率だけで説明（時間の流れなし）
fit2 = sm.OLS(d.up10, sm.add_constant(d[["jobs_ratio"]])).fit()
out["only_ratio_coef"] = r3(fit2.params["jobs_ratio"]); out["only_ratio_part"] = r3(fit2.params["jobs_ratio"] * dr)
d["resid_only_ratio"] = fit2.resid
out["resid_only_ratio_2007_2012_mean"] = r3(d[d.year <= 2012].resid_only_ratio.mean())
out["resid_only_ratio_2020_2025_mean"] = r3(d[d.year >= 2020].resid_only_ratio.mean())
# 倍率が近い年どうしの比較（倍率の差 0.1 以内で、10年以上離れた組）
pairs = []
yy = d.set_index("year")
for a in yy.index:
    for b in yy.index:
        if b - a >= 10 and abs(yy.jobs_ratio[a] - yy.jobs_ratio[b]) <= 0.10:
            pairs.append(dict(year_a=int(a), year_b=int(b), ratio_a=r3(yy.jobs_ratio[a]), ratio_b=r3(yy.jobs_ratio[b]),
                              up10_a=r3(yy.up10[a]), up10_b=r3(yy.up10[b]), diff=r3(yy.up10[b] - yy.up10[a])))
pp = pd.DataFrame(pairs).sort_values(["year_a", "year_b"])
pp.to_csv(RES / "requestion_pairs.csv", index=False)
out["n_pairs"] = int(len(pp)); out["pairs_diff_median"] = r3(pp["diff"].median()); out["pairs_diff_min"] = r3(pp["diff"].min()); out["pairs_diff_max"] = r3(pp["diff"].max())
(RES / "requestion.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(out, ensure_ascii=False, indent=0)); print(pp.to_string())

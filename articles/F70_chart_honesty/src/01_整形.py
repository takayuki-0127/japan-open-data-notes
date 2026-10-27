# 前の記事（F02・F12・F44）で取ったデータを、年次・月次の表に整える
import pandas as pd, pathlib
R = pathlib.Path(__file__).resolve().parents[1] / "data"
b = pd.read_csv(R/"raw/births_monthly_f02.csv")
ind = pd.read_csv(R/"raw/indicators_f12.csv", parse_dates=["month"])
tfr = pd.read_csv(R/"raw/tfr_f44.csv")
ind["year"] = ind.month.dt.year
# 年次：出生数（合計）、消費者物価（年平均）、就業者（年平均）、失業率（年平均）、実質賃金指数（年平均）
ann = (b.groupby("year").births.sum().to_frame()
       .join(ind.groupby("year")[["cpi_all","employed_sa_10k","unemp_rate_sa","real_wage_total_idx","jobs_ratio_sa"]].mean())
       .join(tfr[tfr.pref=="全国"].set_index("year").tfr))
ann = ann[(ann.index>=2000)&(ann.index<=2025)]
ann.to_csv(R/"annual.csv", float_format="%.4f")
# 月次：実質賃金の12か月移動平均（ボーナス月の振れをならす）
m = ind[["month","real_wage_total_idx","cpi_all","jobs_ratio_sa","unemp_rate_sa"]].copy()
m["real_wage_12m"] = m.real_wage_total_idx.rolling(12).mean()
m.to_csv(R/"monthly.csv", index=False, float_format="%.4f")
b.to_csv(R/"births_monthly.csv", index=False)
print(ann.tail(3)); print(len(m))

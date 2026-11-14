"""711 月の売上を「30」で割るか、その月の日数や営業日数で割るかで、日あたりの前月比はどれだけ違うのか

架空の店の日次売上（2024-01〜2025-12）。毎週水曜と年末年始（12/31〜1/3）は休業で、行がない。
1営業日あたりの売上の水準は2年間一定（曜日の波と日々のゆれだけ）に置く。月の売上を
  30で割る／暦の日数で割る／営業日数で割る
の3通りで日あたりにし、前月比の見かけの振れを比べる。DuckDB（1スレッド）と pandas で一致を確かめる。seed 711。
"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, LIGHT, GREEN

DATA.mkdir(exist_ok=True)
SRC = "出典：架空の店の日次売上（作成者が乱数で作成、seed 711）"
rng = np.random.default_rng(711)
days = pd.date_range("2024-01-01", "2025-12-31")
closed = (days.weekday == 2) | (((days.month == 12) & (days.day == 31)) | ((days.month == 1) & (days.day <= 3)))
open_days = days[~closed]
wk = {0: 0.9, 1: 0.9, 3: 0.95, 4: 1.1, 5: 1.35, 6: 1.25}  # 水曜は休み
v = np.array([wk[d.weekday()] for d in open_days]) * 200000 * rng.lognormal(0, 0.08, len(open_days))
D = pd.DataFrame({"sale_date": open_days, "sales": np.round(v).astype(int)})
D.assign(sale_date=D.sale_date.dt.strftime("%Y-%m-%d")).to_csv(DATA / "daily.csv", index=False)

con = duckdb.connect(); con.execute("SET threads=1"); con.register("daily", D)
Q = con.execute((SQL / "02_daily_duckdb.sql").read_text(encoding="utf-8")).df().set_index("ym")
g = D.groupby(D.sale_date.dt.to_period("M"))
T = pd.DataFrame({"month_sales": g.sales.sum(), "business_days": g.size()})
T["calendar_days"] = T.index.days_in_month
T["per_day_30"] = T.month_sales / 30; T["per_day_calendar"] = T.month_sales / T.calendar_days; T["per_day_business"] = T.month_sales / T.business_days
T.index = T.index.to_timestamp()
for c in ["per_day_30", "per_day_calendar", "per_day_business"]:
    assert np.allclose(T[c].values, Q[c].values)
M = {"per_day_30": "30で割る", "per_day_calendar": "暦の日数で割る", "per_day_business": "営業日数で割る"}
mom = pd.DataFrame({k: (T[k] / T[k].shift() - 1) * 100 for k in M}).dropna()
T.round(1).to_csv(RES / "monthly.csv"); mom.round(2).to_csv(RES / "mom.csv")
f24 = pd.Timestamp("2024-03-01"); f25 = pd.Timestamp("2025-03-01")
out = {"period": "2024-01〜2025-12", "closed": "毎週水曜・12/31〜1/3", "true_level": "1営業日あたりの水準は一定（曜日の波だけ）",
       "mom_sd_pt": {M[k]: round(float(mom[k].std()), 2) for k in M},
       "mom_max_abs_pt": {M[k]: round(float(mom[k].abs().max()), 1) for k in M},
       "mar_vs_feb_2024": {M[k]: round(float(mom.loc[f24, k]), 1) for k in M},
       "mar_vs_feb_2025": {M[k]: round(float(mom.loc[f25, k]), 1) for k in M},
       "jan_2025_vs_dec_2024": {M[k]: round(float(mom.loc[pd.Timestamp("2025-01-01"), k]), 1) for k in M},
       "business_days_range": [int(T.business_days.min()), int(T.business_days.max())]}
json.dump(out, open(RES / "a711_main.json", "w"), ensure_ascii=False, indent=1)
cols = {"per_day_30": ORANGE, "per_day_calendar": BLUE, "per_day_business": GREEN}
# 図1：日あたりの推移
fig, ax = plt.subplots(figsize=(8.5, 3.8))
for k, lab in M.items():
    ax.plot(T.index, T[k] / 1e4, "o-", ms=3, color=cols[k], label=lab)
ax.set_ylabel("日あたりの売上（万円）"); ax.legend(frameon=False, fontsize=9)
ax.set_title("水準は一定なのに、30で割ると31日の月が高く、2月が低く出る")
save(fig, "a711_per_day.png", SRC)
# 図2：前月比
fig, ax = plt.subplots(figsize=(8.5, 3.8)); w = 8
for i, (k, lab) in enumerate(M.items()):
    ax.bar(mom.index + pd.Timedelta(days=(i - 1) * w), mom[k], width=w, color=cols[k], label=lab)
ax.axhline(0, color=GRAY, lw=0.8); ax.set_ylabel("日あたりの前月比（%）"); ax.legend(frameon=False, fontsize=9, ncol=3)
ax.set_title("本当の変化は0。30で割ると3月は+10%前後、営業日数で割ると曜日の並びの分だけ残る")
save(fig, "a711_mom.png", SRC)
# 図3：前月比の振れの大きさ
fig, ax = plt.subplots(figsize=(7, 3.6))
sd = [mom[k].std() for k in M]
ax.bar(list(M.values()), sd, color=[cols[k] for k in M])
for i, s in enumerate(sd):
    ax.text(i, s + 0.1, f"{s:.1f}", ha="center")
ax.set_ylabel("前月比の標準偏差（ポイント）")
ax.set_title("見かけの前月比の振れ：営業日数で割ると半分以下。暦の日数では小さくならない")
save(fig, "a711_sd.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))

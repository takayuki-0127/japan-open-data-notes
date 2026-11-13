"""593 開店と閉店がある期間で、「1店あたりの売上」を月末の店数で割るか、平均の店数か、営業日数で割るかで、どれだけ違うのか。
架空のチェーン（月の途中の開閉店を含む、2023〜2025年の日次売上。seed 593）"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from common import DATA, SQL, RES, save, BLUE, ORANGE, GRAY, INK, GREEN

SRC = "出典：架空のチェーンの店舗と日次売上（作成者が乱数で作成、seed 593）"
rng = np.random.default_rng(593)
D0, D1 = pd.Timestamp("2023-01-01"), pd.Timestamp("2025-12-31")
days = pd.date_range(D0, D1, freq="D")

# ---- 1. 店：最初からある80店＋期間中に開く店。一部は閉まる ----
st = []
for i in range(80):
    st.append([D0 - pd.Timedelta(days=int(rng.integers(400, 3000))), pd.NaT])
# 開店：毎月0〜2店をランダムな日に。2024年10月25日には12店をまとめて開く
for m in pd.date_range("2023-02-01", "2025-12-01", freq="MS"):
    for _ in range(rng.choice([0, 1, 1, 2])):
        st.append([m + pd.Timedelta(days=int(rng.integers(0, m.days_in_month))), pd.NaT])
for _ in range(12):
    st.append([pd.Timestamp("2024-10-25"), pd.NaT])
stores = pd.DataFrame(st, columns=["open_date", "close_date"])
# 閉店：開店から1年以上たった店のうち、毎月0〜1店。2025年3月31日には8店をまとめて閉じる
cand = list(stores.index[:80])
for m in pd.date_range("2023-03-01", "2025-12-01", freq="MS"):
    if rng.random() < 0.55:
        j = cand.pop(int(rng.integers(len(cand))))
        stores.loc[j, "close_date"] = m + pd.Timedelta(days=int(rng.integers(0, m.days_in_month)))
for j in [cand.pop(int(rng.integers(len(cand)))) for _ in range(8)]:
    stores.loc[j, "close_date"] = pd.Timestamp("2025-03-31")
stores.insert(0, "store_id", [f"S{i + 1:03d}" for i in range(len(stores))])
stores["base"] = rng.lognormal(np.log(30), 0.3, len(stores))      # 1日の売上の水準（万円）

# ---- 2. 日次売上（営業している日だけ行がある） ----
season = {1: 0.95, 2: 0.88, 3: 1.0, 4: 0.98, 5: 1.02, 6: 0.95, 7: 1.05, 8: 1.1, 9: 0.96, 10: 1.0, 11: 1.0, 12: 1.2}
trend = lambda d: 1 + 0.02 * (d - D0).days / 365      # 店の売上の水準は年2%ずつ伸びる
rows = []
for r in stores.itertuples():
    a = max(r.open_date, D0); b = min(r.close_date, D1) if pd.notna(r.close_date) else D1
    dd = pd.date_range(a, b, freq="D")
    if len(dd) == 0:
        continue
    age = (dd - r.open_date).days.values
    ramp = np.where(age < 90, 0.75 + 0.25 * age / 90, 1.0)          # 開店から3か月は控えめ
    s = r.base * np.array([season[m] for m in dd.month]) * np.array([trend(x) for x in dd]) * ramp * rng.lognormal(0, 0.12, len(dd))
    rows.append(pd.DataFrame({"sold_on": dd, "store_id": r.store_id, "amount": np.round(s * 10000).astype(int)}))
sales = pd.concat(rows).sort_values(["sold_on", "store_id"]).reset_index(drop=True)
sales.to_csv(DATA / "daily_sales.csv", index=False, date_format="%Y-%m-%d")
stores[["store_id", "open_date", "close_date"]].to_csv(DATA / "stores.csv", index=False, date_format="%Y-%m-%d")

# ---- 3. 月次の3つの分母 ----
months = pd.date_range(D0, D1, freq="MS")
recs = []
for m in months:
    me = m + pd.offsets.MonthEnd(0)
    op, cl = stores.open_date, stores.close_date.fillna(pd.Timestamp("2200-12-31"))
    end = int(((op <= me) & (cl > me)).sum())
    begin = int(((op <= m) & (cl >= m)).sum())
    a = op.clip(lower=m); b = cl.clip(upper=me)
    sd = int(np.clip((b - a).dt.days + 1, 0, None).sum())
    amt = int(sales.loc[(sales.sold_on >= m) & (sales.sold_on <= me), "amount"].sum())
    recs.append((m, amt, end, begin, sd, m.days_in_month,
                 int(((op >= m) & (op <= me)).sum()), int(((stores.close_date >= m) & (stores.close_date <= me)).sum())))
mo = pd.DataFrame(recs, columns=["month", "amount", "stores_end", "stores_begin", "store_days", "days", "opened", "closed"])
mo["per_end"] = mo.amount / mo.stores_end
mo["per_avg"] = mo.amount / ((mo.stores_begin + mo.stores_end) / 2)
mo["per_days"] = mo.amount / mo.store_days * mo.days
for c in ["end", "avg"]:
    mo[f"dev_{c}"] = (mo[f"per_{c}"] / mo.per_days - 1) * 100
for c in ["end", "avg", "days"]:
    mo[f"yoy_{c}"] = (mo[f"per_{c}"] / mo[f"per_{c}"].shift(12) - 1) * 100
mo.to_csv(RES / "monthly.csv", index=False, float_format="%.4f", date_format="%Y-%m")

y = mo.dropna(subset=["yoy_days"])
gap_end = (y.yoy_end - y.yoy_days); gap_avg = (y.yoy_avg - y.yoy_days)
oct24 = mo[mo.month == "2024-10-01"].iloc[0]; mar25 = mo[mo.month == "2025-03-01"].iloc[0]; apr25 = mo[mo.month == "2025-04-01"].iloc[0]
res = {"n_stores_total": int(len(stores)), "n_opened_in_period": int((stores.open_date >= D0).sum()), "n_closed_in_period": int(stores.close_date.notna().sum()),
       "store_days_total": int(mo.store_days.sum()), "n_rows": int(len(sales)),
       "dev_vs_open_days_pct": {c: {"min": round(float(mo[f"dev_{c}"].min()), 1), "max": round(float(mo[f"dev_{c}"].max()), 1),
                                    "median_abs": round(float(mo[f"dev_{c}"].abs().median()), 2), "n_months_abs_over_2": int((mo[f"dev_{c}"].abs() > 2).sum())} for c in ["end", "avg"]},
       "oct2024_batch_open_12": {"stores_end": int(oct24.stores_end), "stores_begin": int(oct24.stores_begin),
                                 "dev_end": round(float(oct24.dev_end), 1), "dev_avg": round(float(oct24.dev_avg), 1)},
       "mar2025_batch_close_8": {"stores_end": int(mar25.stores_end), "dev_end": round(float(mar25.dev_end), 1), "dev_avg": round(float(mar25.dev_avg), 1)},
       "yoy_gap_vs_open_days_pt": {"end": {"max_abs": round(float(gap_end.abs().max()), 1), "median_abs": round(float(gap_end.abs().median()), 2)},
                                   "avg": {"max_abs": round(float(gap_avg.abs().max()), 1), "median_abs": round(float(gap_avg.abs().median()), 2)}},
       "yoy_sign_differs_from_open_days": {"end": int((np.sign(y.yoy_end) != np.sign(y.yoy_days)).sum()), "avg": int((np.sign(y.yoy_avg) != np.sign(y.yoy_days)).sum()), "n_months": int(len(y))},
       "yoy_oct2025": {c: round(float(mo.loc[mo.month == "2025-10-01", f"yoy_{c}"].iloc[0]), 1) for c in ["end", "avg", "days"]},
       "yoy_apr2025": {c: round(float(apr25[f"yoy_{c}"]), 1) for c in ["end", "avg", "days"]},
       "year_total_per_store_2025": {"end_dec": round(float(mo[mo.month.dt.year == 2025].amount.sum() / mo[mo.month == "2025-12-01"].stores_end.iloc[0] / 1e4), 0),
                                     "store_days": round(float(mo[mo.month.dt.year == 2025].amount.sum() / mo[mo.month.dt.year == 2025].store_days.sum() * 365 / 1e4), 0)}}

# ---- 4. SQL（DuckDB、1スレッド） ----
con = duckdb.connect(); con.execute("SET threads=1")
con.execute(f"CREATE TABLE daily_sales AS SELECT * FROM read_csv_auto('{DATA / 'daily_sales.csv'}')")
con.execute(f"CREATE TABLE stores AS SELECT store_id, CAST(open_date AS DATE) AS open_date, TRY_CAST(close_date AS DATE) AS close_date FROM read_csv_auto('{DATA / 'stores.csv'}', all_varchar=true)")
sq = con.execute((SQL / "02_per_store_duckdb.sql").read_text()).df()
sq.to_csv(RES / "sql_monthly.csv", index=False, float_format="%.4f")
res["sql_match_python"] = bool((sq.stores_end.values == mo.stores_end.values).all() and (sq.stores_begin.values == mo.stores_begin.values).all()
                               and (sq.store_days.values == mo.store_days.values).all()
                               and np.allclose(sq[["per_store_month_end", "per_store_avg", "per_store_open_days"]].values, mo[["per_end", "per_avg", "per_days"]].values))
json.dump(res, open(RES / "a593_main.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False, indent=1))

# ---- 5. 図 ----
lab = {"end": "月末の店数で割る", "avg": "月初と月末の平均で割る", "days": "営業日数（店×日）で割る"}
col = {"end": ORANGE, "avg": GREEN, "days": BLUE}
fig, ax = plt.subplots(figsize=(9, 4.4))
w = mo[(mo.month >= "2024-07-01") & (mo.month <= "2025-06-01")]
for c in ["end", "avg", "days"]:
    ax.plot(w.month, w[f"per_{c}"] / 1e4, color=col[c], lw=1.8 if c != "days" else 2.4, marker="o", ms=4, label=lab[c])
ax.set_ylabel("1店あたりの月の売上（万円）")
ax.annotate("12店を10/25に開店", xy=(pd.Timestamp("2024-10-01"), oct24.per_end / 1e4), xytext=(pd.Timestamp("2024-08-10"), oct24.per_end / 1e4 - 70),
            arrowprops=dict(arrowstyle="->", color=GRAY), fontsize=9, color=INK)
ax.annotate("8店を3/31に閉店", xy=(pd.Timestamp("2025-03-01"), mar25.per_end / 1e4), xytext=(pd.Timestamp("2025-04-01"), mar25.per_end / 1e4 + 50),
            arrowprops=dict(arrowstyle="->", color=GRAY), fontsize=9, color=INK)
ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y/%-m"))
ax.set_title("同じ売上でも、分母の取り方で「1店あたり」が動く（2024年7月〜2025年6月）")
ax.legend(frameon=False, fontsize=9, loc="upper left")
save(fig, "a593_per_store.png", SRC)

fig, axes = plt.subplots(2, 1, figsize=(9, 5.4), sharex=True, gridspec_kw={"height_ratios": [2.2, 1]})
ax = axes[0]
ax.bar(mo.month - pd.Timedelta(days=7), mo.dev_end, width=13, color=ORANGE, label=lab["end"])
ax.bar(mo.month + pd.Timedelta(days=7), mo.dev_avg, width=13, color=GREEN, label=lab["avg"])
ax.axhline(0, color=INK, lw=0.8)
ax.set_ylabel("営業日数で割った値との差（%）"); ax.legend(frameon=False, fontsize=9, loc="lower left")
ax.set_title("開店・閉店の多い月ほど、分母によるずれが大きい")
ax = axes[1]
ax.bar(mo.month, mo.opened, width=20, color=BLUE, label="開店")
ax.bar(mo.month, -mo.closed, width=20, color=GRAY, label="閉店")
ax.axhline(0, color=INK, lw=0.6); ax.set_ylabel("店数"); ax.legend(frameon=False, fontsize=9, ncol=2, loc="upper left")
ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y/%-m"))
save(fig, "a593_deviation.png", SRC)

fig, ax = plt.subplots(figsize=(9, 4.2))
yy = mo[mo.month >= "2024-01-01"]
for c in ["end", "avg", "days"]:
    ax.plot(yy.month, yy[f"yoy_{c}"], color=col[c], lw=1.8 if c != "days" else 2.4, marker="o", ms=3, label=lab[c])
ax.axhline(0, color=INK, lw=0.8)
ax.set_ylabel("1店あたり売上の前年同月比（%）")
ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y/%-m"))
ax.set_title("前年同月比も、分母しだいで別の数字になる（店の実力は年2%の伸びで置いた）")
ax.legend(frameon=False, fontsize=9, loc="upper left")
save(fig, "a593_yoy.png", SRC)

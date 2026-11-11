"""232：前年同月比と12か月移動平均を SQL のウィンドウ関数で出し、pandas の計算と照合する。
月が1つ抜けたときに LAG(…,12) がどれだけずれるかも試す"""
import duckdb, numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import DATA, SQL, RES, save, tsql_to_duckdb, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

con = duckdb.connect()
con.execute("CREATE SCHEMA dbo")
con.execute(f"CREATE TABLE dbo.sales_monthly AS SELECT gyotai, CAST(ym AS DATE) AS ym, CAST(sales AS BIGINT) AS sales "
            f"FROM read_csv_auto('{DATA / 'meti_sales_monthly.csv'}')")
q2 = tsql_to_duckdb((SQL / "02_yoy_ma.sql").read_text())
q3 = tsql_to_duckdb((SQL / "03_yoy_calendar.sql").read_text())
q4 = tsql_to_duckdb((SQL / "04_check_gaps.sql").read_text())
r = con.execute(q2).df()
r["ma12"] = np.where(r.ma12_n == 12, r.ma12_raw, np.nan)

# pandas で同じものを計算して照合
p = pd.read_csv(DATA / "meti_sales_monthly.csv", parse_dates=["ym"]).sort_values(["gyotai", "ym"])
p["yoy_pd"] = p.groupby("gyotai").sales.pct_change(12)
p["ma12_pd"] = p.groupby("gyotai").sales.transform(lambda s: s.rolling(12).mean())
m = r.merge(p[["gyotai", "ym", "yoy_pd", "ma12_pd"]], on=["gyotai", "ym"])
chk = {"rows": len(r), "yoy_maxdiff": float(np.nanmax(np.abs(m.yoy - m.yoy_pd))),
       "ma12_maxdiff": float(np.nanmax(np.abs(m.ma12 - m.ma12_pd))),
       "yoy_null_rows": int(r.yoy.isna().sum()), "ma12_partial_rows": int((r.ma12_n < 12).sum()),
       "gaps_full_data": len(con.execute(q4).df())}
r.to_csv(RES / "yoy_ma12_by_sql.csv", index=False)

# 落とし穴：コンビニの 2020-05 の行が抜けていたら
con.execute("CREATE TABLE dbo.full_copy AS SELECT * FROM dbo.sales_monthly")
con.execute("DELETE FROM dbo.sales_monthly WHERE gyotai='コンビニ' AND ym=DATE '2020-05-01'")
gaps = con.execute(q4).df()
lag_bad = con.execute(q2).df().query("gyotai=='コンビニ'")[["ym", "yoy"]].rename(columns={"yoy": "yoy_lag"})
cal = con.execute(q3).df().query("gyotai=='コンビニ'")[["ym", "yoy"]].rename(columns={"yoy": "yoy_cal"})
truth = m.query("gyotai=='コンビニ'")[["ym", "yoy_pd"]]
g = truth.merge(lag_bad, on="ym", how="left").merge(cal, on="ym", how="left")
g["err_lag_pt"] = (g.yoy_lag - g.yoy_pd) * 100
g["err_cal_pt"] = (g.yoy_cal - g.yoy_pd) * 100
wrong = g[(g.err_lag_pt.abs() > 1e-9)]
chk.update({"missing_month": "コンビニ 2020-05", "gaps_found": gaps.astype(str).to_dict("records"),
            "lag_wrong_months": int(len(wrong)), "lag_wrong_first": str(wrong.ym.min().date()), "lag_wrong_last": str(wrong.ym.max().date()),
            "lag_err_max_abs_pt": float(wrong.err_lag_pt.abs().max()), "lag_err_mean_abs_pt": float(wrong.err_lag_pt.abs().mean()),
            "cal_wrong_months_excluding_missing_neighbors": int((g.err_cal_pt.abs() > 1e-9).sum()),
            "cal_null_months": int(g.yoy_cal.isna().sum() - g.yoy_pd.isna().sum())})
g.to_csv(RES / "missing_month_test.csv", index=False)

# 最新の前年同月比（2026-08）
last = r[r.ym == r.ym.max()][["gyotai", "ym", "sales", "yoy", "ma12"]]
last.to_csv(RES / "latest.csv", index=False)
chk["latest"] = {k: round(float(v) * 100, 1) for k, v in zip(last.gyotai, last.yoy)}
pd.Series(chk).to_json(RES / "checks.json", force_ascii=False, indent=1)
print(chk)

# 図1：6業態の前年同月比（2019年〜）
fig, ax = plt.subplots(figsize=(8, 4.2))
cols = {"ドラッグストア": BLUE, "スーパー": GREEN, "コンビニ": ORANGE, "百貨店": INK, "ホームセンター": GRAY, "家電大型専門店": LIGHT}
for k, c in cols.items():
    s = r[(r.gyotai == k) & (r.ym >= "2019-01-01")]
    ax.plot(s.ym, s.yoy * 100, color=c, lw=1.6 if k in ("ドラッグストア", "百貨店", "コンビニ") else 1.0, label=k)
ax.axhline(0, color=GRAY, lw=0.8)
ax.set_ylim(-40, 60); ax.set_ylabel("前年同月比（%）")
ax.set_title("SQL の LAG(販売額, 12) で出した前年同月比（業態別）")
ax.legend(ncol=3, fontsize=9, frameon=False, loc="upper left")
ax.text(0.99, 0.02, "2020〜21年はコロナの影響で上下に大きく振れる（百貨店は表示範囲外の月あり）", transform=ax.transAxes, ha="right", fontsize=8, color=GRAY)
save(fig, "a232_yoy.png")

# 図2：ドラッグストアの月の値と12か月移動平均
s = r[r.gyotai == "ドラッグストア"]
fig, ax = plt.subplots(figsize=(8, 4))
ax.plot(s.ym, s.sales / 1e5, color=LIGHT, lw=1.2, label="毎月の販売額")
ax.plot(s.ym, s.ma12 / 1e5, color=BLUE, lw=2.2, label="12か月移動平均（AVG … ROWS BETWEEN 11 PRECEDING）")
ax.set_ylabel("販売額（千億円）"); ax.legend(frameon=False, fontsize=9, loc="upper left")
ax.set_title("ドラッグストア：月の山谷をならすと、伸びの形が見える")
ax.text(0.30, 0.06, "最初の11か月は、平均する月数が足りないので空けている", transform=ax.transAxes, fontsize=8, color=GRAY)
save(fig, "a232_ma12.png")

# 図3：月が1つ抜けたときの前年同月比のずれ（LAG と日付で結合）
gg = g[(g.ym >= "2019-10-01") & (g.ym <= "2022-01-01")]
fig, ax = plt.subplots(figsize=(8, 4))
x = np.arange(len(gg)); w = 0.4
ax.bar(x - w / 2, gg.err_lag_pt.fillna(0), w, color=ORANGE, label="LAG(…, 12)：行の位置で12前")
ax.bar(x + w / 2, gg.err_cal_pt.fillna(0), w, color=BLUE, label="日付で12か月前と結合（03）")
ax.axhline(0, color=GRAY, lw=0.8)
lab = [d.strftime("%y/%m") if d.month in (1, 5, 9) else "" for d in gg.ym]
ax.set_xticks(x); ax.set_xticklabels(lab, fontsize=8)
ax.set_ylabel("正しい前年同月比とのずれ（ポイント）")
ax.set_title("コンビニの2020年5月の行が抜けていたら（試しに1行消した）")
ax.text(0.99, 0.04, "日付で結合した方はずれ0（抜けた2020年5月と、その1年後の2021年5月は NULL になる）", transform=ax.transAxes, ha="right", fontsize=8, color=BLUE)
ax.legend(frameon=False, fontsize=9)
save(fig, "a232_missing.png")

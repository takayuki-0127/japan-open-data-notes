"""243：縦長の統計表を、SQL で横長のレポートの形にする（CASE WHEN／PIVOT）。
形を変えたときに起きる3つの落とし穴（列にない値・重複・UNPIVOT の NULL）を試し、照合のクエリで見つかるか確かめる"""
import json
import duckdb, numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import DATA, SQL, RES, save, tsql_to_duckdb, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

COLS = ["conveni", "super", "drug", "homecenter", "kaden", "depart"]
JP = {"conveni": "コンビニ", "super": "スーパー", "drug": "ドラッグストア", "homecenter": "ホームセンター", "kaden": "家電大型専門店", "depart": "百貨店"}


def fresh():
    con = duckdb.connect()
    con.execute("CREATE SCHEMA dbo")
    con.execute(f"CREATE TABLE dbo.sales_monthly AS SELECT gyotai, CAST(ym AS DATE) AS ym, CAST(sales AS BIGINT) AS sales "
                f"FROM read_csv_auto('{DATA / 'meti_sales_monthly.csv'}')")
    return con


q2 = tsql_to_duckdb((SQL / "02_wide_casewhen.sql").read_text())
q5a, q5b = [tsql_to_duckdb(x) for x in (SQL / "05_checks.sql").read_text().split("-- (b)")]
q5b = "-- (b)" + q5b

con = fresh()
long_rows = con.execute("SELECT COUNT(*) FROM dbo.sales_monthly").fetchone()[0]
w = con.execute(q2).df()
# DuckDB の PIVOT（列の値を表から自動で読む）でも同じ表になるか
dp = con.execute("""PIVOT (SELECT YEAR(ym) AS yr, gyotai, sales FROM dbo.sales_monthly WHERE ym < DATE '2026-01-01')
                    ON gyotai USING SUM(sales) ORDER BY yr""").df()
# pandas でも
p = pd.read_csv(DATA / "meti_sales_monthly.csv", parse_dates=["ym"])
p = p[p.ym < "2026-01-01"]
pp = p.assign(yr=p.ym.dt.year).pivot_table(index="yr", columns="gyotai", values="sales", aggfunc="sum")
diff_duck = max(abs(w[c].values - dp[JP[c]].values).max() for c in COLS)
diff_pd = max(abs(w[c].values - pp[JP[c]].values).max() for c in COLS)
w.to_csv(RES / "wide_year_by_gyotai.csv", index=False)
chk = {"long_rows": int(long_rows), "wide_rows": len(w), "wide_cols": len(COLS),
       "casewhen_vs_duckdb_pivot_maxdiff": int(diff_duck), "casewhen_vs_pandas_maxdiff": int(diff_pd),
       "rows_per_year": sorted(set(int(x) for x in w.n_rows))}


def total_check(con):
    r = con.execute(q5b).fetchone()
    return int(r[0]), int(r[1])


tl, tc = total_check(con)
scen = [{"case": "そのまま", "total_long": tl, "total_cols": tc, "dup_keys": len(con.execute(q5a).df())}]

# 落とし穴1：新しい業態が増えた（試しに架空の「新業態」を2025年に12行足す）
c1 = fresh()
c1.execute("INSERT INTO dbo.sales_monthly SELECT '新業態（試し）', ym, CAST(sales*0.1 AS BIGINT) FROM dbo.sales_monthly "
           "WHERE gyotai='コンビニ' AND YEAR(ym)=2025")
w1 = c1.execute(q2).df()
dp1 = c1.execute("""PIVOT (SELECT YEAR(ym) AS yr, gyotai, sales FROM dbo.sales_monthly WHERE ym < DATE '2026-01-01')
                    ON gyotai USING SUM(sales) ORDER BY yr""").df()
tl1, tc1 = total_check(c1)
scen.append({"case": "列にない業態が増えた", "total_long": tl1, "total_cols": tc1, "dup_keys": len(c1.execute(q5a).df()),
             "casewhen_cols": len(COLS), "duckdb_pivot_cols": len(dp1.columns) - 1,
             "n_rows_2025_casewhen": int(w1.loc[w1.yr == 2025, "n_rows"].iloc[0])})

# 落とし穴2：同じ月の行が2回入った（コンビニ 2025-03 を二重に取り込んだ）
c2 = fresh()
c2.execute("INSERT INTO dbo.sales_monthly SELECT * FROM dbo.sales_monthly WHERE gyotai='コンビニ' AND ym=DATE '2025-03-01'")
w2 = c2.execute(q2).df()
dupv = int(c2.execute("SELECT sales FROM dbo.sales_monthly WHERE gyotai='コンビニ' AND ym=DATE '2025-03-01' LIMIT 1").fetchone()[0])
tl2, tc2 = total_check(c2)
d = c2.execute(q5a).df()
scen.append({"case": "同じ月の行が2回入った", "total_long": tl2, "total_cols": tc2, "dup_keys": len(d),
             "conveni_2025_correct": int(w.loc[w.yr == 2025, "conveni"].iloc[0]),
             "conveni_2025_with_dup": int(w2.loc[w2.yr == 2025, "conveni"].iloc[0]),
             "dup_row_value": dupv})
# MAX で集計すると重複は見えなくなる（合計を出したい表では使えない）

# 落とし穴3：横長（月×年）を縦に戻すと、空いたセルの行が消える
c3 = fresh()
c3.execute("""CREATE TABLE wide_m AS PIVOT (SELECT MONTH(ym) AS m, YEAR(ym) AS yr, sales FROM dbo.sales_monthly WHERE gyotai='コンビニ')
              ON yr USING SUM(sales) ORDER BY m""")
cells = c3.execute("SELECT COUNT(*) FROM wide_m").fetchone()[0] * (len(c3.execute("SELECT * FROM wide_m LIMIT 1").df().columns) - 1)
nulls = int(c3.execute("SELECT COUNT(*) FROM wide_m WHERE \"2026\" IS NULL").fetchone()[0])
back = c3.execute("UNPIVOT wide_m ON COLUMNS(* EXCLUDE (m)) INTO NAME yr VALUE sales").df()
ycols = ", ".join(f'"{c}"' for c in c3.execute("SELECT * FROM wide_m LIMIT 1").df().columns if c != "m")
back_null = c3.execute(f"SELECT * FROM wide_m UNPIVOT INCLUDE NULLS (sales FOR yr IN ({ycols}))").df()
long_conv = int(c3.execute("SELECT COUNT(*) FROM dbo.sales_monthly WHERE gyotai='コンビニ'").fetchone()[0])
scen.append({"case": "横長を縦に戻した（UNPIVOT）", "wide_cells": int(cells), "null_cells": nulls,
             "unpivot_rows": len(back), "unpivot_include_nulls_rows": len(back_null), "long_rows_conveni": long_conv})

chk["scenarios"] = scen
json.dump(chk, open(RES / "checks.json", "w"), ensure_ascii=False, indent=1)
pd.DataFrame(scen).to_csv(RES / "scenarios.csv", index=False)
print(json.dumps(chk, ensure_ascii=False, indent=1))

# 図1：レポートの形（年×業態、兆円）を表の画像に
show = w[w.yr >= 2016].copy()
fig, ax = plt.subplots(figsize=(9.2, 4.1)); ax.axis("off")
hdr = ["年"] + [JP[c] for c in COLS]
cell = [[str(int(r.yr))] + [f"{r[c] / 1e6:.2f}" for c in COLS] for _, r in show.iterrows()]
t = ax.table(cellText=cell, colLabels=hdr, loc="center", cellLoc="right", colLoc="center", colWidths=[0.08] + [0.15] * 6)
t.auto_set_font_size(False); t.set_fontsize(9.5); t.scale(1, 1.32)
for (i, j), c in t.get_celld().items():
    c.set_edgecolor("#dddddd")
    if i == 0: c.set_facecolor("#eef3fb"); c.set_text_props(weight="bold")
ax.set_title("縦長の912行（業態・月・販売額）を、年×業態の表にした（兆円）", fontsize=12)
save(fig, "a243_wide_table.png", y=0.03)

# 図2：3つの落とし穴で、照合の数字がどう動くか
fig, axs = plt.subplots(1, 3, figsize=(10, 3.6))
ax = axs[0]
ax.bar(["縦長の合計", "列の合計"], [tl1 / 1e6, tc1 / 1e6], color=[BLUE, ORANGE])
ax.set_ylim(min(tl1, tc1) / 1e6 * 0.999, max(tl1, tc1) / 1e6 * 1.0016)
ax.set_title("① 列にない業態が増えた", fontsize=11)
ax.text(0.5, 0.92, f"差 {(tl1 - tc1) / 100:,.0f}億円\n（足した架空の業態の分）\nCASE WHEN では黙って落ちる", transform=ax.transAxes, ha="center", va="top", fontsize=8.5)
ax.set_ylabel("2014〜25年の合計（兆円）")
ax = axs[1]
v = [scen[2]["conveni_2025_correct"] / 100, scen[2]["conveni_2025_with_dup"] / 100]
ax.bar(["正しい値", "重複あり"], v, color=[BLUE, ORANGE]); ax.set_ylim(min(v) * 0.97, max(v) * 1.045)
ax.set_title("② 同じ月の行が2回入った", fontsize=11)
ax.text(0.5, 0.92, f"コンビニ2025年が{(v[1] - v[0]):,.0f}億円多く出る\n(a) の重複チェックで1件見つかる", transform=ax.transAxes, ha="center", va="top", fontsize=8.5)
ax.set_ylabel("コンビニ 2025年（億円）")
ax = axs[2]
s3 = scen[3]
ax.bar(["元の縦長", "UNPIVOT", "INCLUDE\nNULLS"], [s3["long_rows_conveni"], s3["unpivot_rows"], s3["unpivot_include_nulls_rows"]], color=[BLUE, ORANGE, GRAY])
ax.set_ylim(140, 162)
ax.set_title("③ 横長を縦に戻した", fontsize=11)
ax.text(0.5, 0.95, f"2026年9〜12月の空きセル{s3['null_cells']}個：\n普通は落とす／INCLUDE NULLS は残す", transform=ax.transAxes, ha="center", va="top", fontsize=8.5)
ax.set_ylabel("行数（コンビニ）")
fig.suptitle("形を変えたときの3つの落とし穴と、照合の数字", fontsize=12.5, y=1.02)
fig.tight_layout()
save(fig, "a243_pitfalls.png", y=-0.03)

# 図3：書き方の比較表
fig, ax = plt.subplots(figsize=(10, 3.0)); ax.axis("off")
rows = [["CASE WHEN ＋ SUM", "列を手で書く", "多くのDBで同じ文", "増えた分は落ちる", "DuckDB で検証"],
        ["T-SQL の PIVOT", "列を手で書く", "SQL Server 専用", "増えた分は落ちる", "未検証"],
        ["動的 SQL ＋ PIVOT", "表から読む", "SQL Server 専用", "列が自動で増える", "未検証"],
        ["DuckDB の PIVOT", "表から読む", "DuckDB 専用", "列が自動で増える", "DuckDB で検証"]]
t = ax.table(cellText=rows, colLabels=["書き方", "列（業態）", "動く所", "業態が増えたとき", "この記事"], loc="center", cellLoc="left", colLoc="center", colWidths=[0.2, 0.13, 0.22, 0.24, 0.16])
t.auto_set_font_size(False); t.set_fontsize(9.5); t.scale(1, 1.55)
for (i, j), c in t.get_celld().items():
    c.set_edgecolor("#dddddd")
    if i == 0: c.set_facecolor("#eef3fb"); c.set_text_props(weight="bold")
ax.set_title("縦長を横長にする4つの書き方", fontsize=12)
save(fig, "a243_methods.png", y=0.08)

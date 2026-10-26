"""02 読み込み：data/raw/ のファイルを整形して DuckDB の raw テーブルに入れる。

- raw_cpi / raw_lfs / raw_jobs / raw_wage（いずれも month, series, value の縦持ち）
- 取り込むたびに load_log に件数・最新月を記録し、snapshots に全値を残す
- 前回の取り込みとの差分（新しく増えた月・過去の値の改定）を results/diff_*.csv に出す
  --as-of YYYY-MM を付けると、その月までのデータだけを入れる（「先月の実行」を再現する試験用）
"""
import argparse, csv, datetime as dt, json, io
from pathlib import Path
import duckdb, openpyxl

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
DB = ROOT / "data" / "stats.duckdb"

CPI_SERIES = {"総合": "cpi_all", "生鮮食品を除く総合": "cpi_core", "生鮮食品及びエネルギーを除く総合": "cpi_core_core",
              "持家の帰属家賃を除く総合": "cpi_ex_rent", "食料": "cpi_food", "エネルギー": "cpi_energy"}


def ym(y, m):
    return dt.date(int(y), int(m), 1)


def read_cpi():
    rows = list(csv.reader((RAW / "cpi.csv").read_text(encoding="utf-8").splitlines()))
    head = rows[0]
    idx = {CPI_SERIES[h]: i for i, h in enumerate(head) if h in CPI_SERIES}
    out = []
    for r in rows:
        if r and r[0].isdigit() and len(r[0]) == 6:
            for s, i in idx.items():
                if i < len(r) and r[i].strip() not in ("", "-"):
                    out.append((ym(r[0][:4], r[0][4:]), s, float(r[i])))
    return out


def read_lfs():
    ws = openpyxl.load_workbook(RAW / "lfs.xlsx", data_only=True, read_only=True).worksheets[0]  # 季節調整値
    out, year = [], None
    cols = {"labour_force_sa": 4, "employed_sa": 7, "unemployed_sa": 13, "unemp_rate_sa": 19}
    for r in ws.iter_rows(min_row=11, values_only=True):
        if isinstance(r[0], int):
            year = r[0]
        elif isinstance(r[0], str) and r[0].startswith("昭和28"):
            year = 1953
        if r[1] and str(r[1]).endswith("月") and year:
            m = int(str(r[1]).replace("月", ""))
            for s, c in cols.items():
                v = r[c]
                if isinstance(v, (int, float)):
                    out.append((ym(year, m), s, float(v)))
            if m == 12:
                year += 1
    return out


def read_jobs():
    ws = openpyxl.load_workbook(RAW / "jobs.xlsx", data_only=True, read_only=True).worksheets[0]  # パート含む一般
    out = []
    for r in ws.iter_rows(min_row=6, values_only=True):
        if r[0] and str(r[0]).endswith("年") and str(r[0])[:4].isdigit():
            y = int(str(r[0])[:4])
            for m in range(1, 13):
                for s, c in (("jobs_ratio_nsa", 1 + m), ("jobs_ratio_sa", 19 + m)):
                    v = r[c]
                    if isinstance(v, (int, float)):
                        out.append((ym(y, m), s, float(v)))
    return out


def read_wage():
    rows = list(csv.reader((RAW / "wage.csv").read_text(encoding="utf-8").splitlines()))
    out = []
    names = {6: "wage_total", 7: "wage_scheduled", 11: "real_wage_total", 12: "real_wage_scheduled"}
    for r in rows[1:]:
        if len(r) < 13 or r[2] == "CY" or not r[2].strip().isdigit():
            continue
        kind = "idx" if r[0] == "指数" else "yoy"
        for c, s in names.items():
            v = r[c].strip()
            if v not in ("", "-", "…"):
                out.append((ym(r[1], r[2]), f"{s}_{kind}", float(v)))
    return out


def main(as_of=None):
    con = duckdb.connect(str(DB))
    con.execute("create table if not exists load_log(load_id integer, loaded_at timestamp, as_of varchar, tbl varchar, n_rows integer, last_month date)")
    con.execute("create table if not exists snapshots(load_id integer, tbl varchar, month date, series varchar, value double)")
    load_id = con.execute("select coalesce(max(load_id),0)+1 from load_log").fetchone()[0]
    cut = dt.date(int(as_of[:4]), int(as_of[5:7]), 1) if as_of else None
    now = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
    summary = {}
    for tbl, fn in (("raw_cpi", read_cpi), ("raw_lfs", read_lfs), ("raw_jobs", read_jobs), ("raw_wage", read_wage)):
        rows = [r for r in fn() if cut is None or r[0] <= cut]
        con.execute(f"create or replace table {tbl}(month date, series varchar, value double)")
        con.executemany(f"insert into {tbl} values (?,?,?)", rows)
        con.executemany("insert into snapshots values (?,?,?,?,?)", [(load_id, tbl, *r) for r in rows])
        last = max(r[0] for r in rows)
        con.execute("insert into load_log values (?,?,?,?,?,?)", [load_id, now, as_of or "latest", tbl, len(rows), last])
        summary[tbl] = {"rows": len(rows), "last_month": str(last)}
    # 前回との差分
    if load_id > 1:
        diff = con.execute("""
            with a as (select * from snapshots where load_id = ?), b as (select * from snapshots where load_id = ?)
            select coalesce(a.tbl,b.tbl) as tbl, coalesce(a.month,b.month) as month, coalesce(a.series,b.series) as series,
                   b.value as prev, a.value as now,
                   case when b.value is null then 'new' when a.value is null then 'dropped' when abs(a.value-b.value)>1e-9 then 'revised' end as status
            from a full join b on a.tbl=b.tbl and a.month=b.month and a.series=b.series
            where b.value is null or a.value is null or abs(a.value-b.value)>1e-9
            order by 1,3,2""", [load_id, load_id - 1]).fetchdf()
        diff.to_csv(ROOT / "results" / f"diff_load{load_id}_vs_{load_id-1}.csv", index=False)
        summary["diff"] = diff.groupby(["tbl", "status"]).size().reset_index(name="n").to_dict("records")
    con.close()
    print(json.dumps({"load_id": load_id, **summary}, ensure_ascii=False, default=str))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--as-of")
    a = ap.parse_args()
    main(a.as_of)

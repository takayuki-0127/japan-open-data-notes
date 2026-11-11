"""03 整える：届いたファイル（data/raw_synth/）から mart を作り、テストを流す。

- SQL（sql/10_staging.sql → sql/20_mart.sql → sql/30_tests.sql）を DuckDB で実行する。書き方は SQL Server 互換にそろえたが、
  この記事では SQL Server そのものでは動かしていない。
- 同じ処理を pandas でも書き（build_mart_pd）、「どの手当てを抜くと数字がどう狂うか」を 04_分析.py で試すのに使う。
  手当てをすべて入れた pandas 版は SQL 版と一致することを確かめる（results/C_sql_vs_pandas.csv）。
- 実行の流れ：1回目（補正表なし）→ テストで問題を見つける → 補正表（ref_fix_*）を足す → 2回目 → mart/ に書き出す。
会社・数字はすべて架空（合成データ）。
"""
import json, pathlib, re
import numpy as np
import pandas as pd
import duckdb

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw_synth"
TRUTH = ROOT / "data" / "truth"
SQL = ROOT / "sql"
MART = ROOT / "mart"
RES = ROOT / "results"
END_DAY = pd.Timestamp("2026-03-31")
FAR = pd.Timestamp("2099-12-31")

# 分析担当がテストの結果を見て足した補正表（1回目のテストで見つかったもの）
REF_FIX_STORE_CODE = pd.DataFrame(
    [["1020", pd.Timestamp("2025-04-01"), FAR, 16, "map"],      # 16店の新コードが対応表から漏れていた（情報システム部に確認）
     ["9999", pd.Timestamp("2000-01-01"), FAR, None, "exclude"]],  # POS のトレーニング用コード。売上ではない
    columns=["店コード", "有効開始", "有効終了", "店番", "処理"])
REF_FIX_WASTE_UNIT = pd.DataFrame(
    [[19, pd.Timestamp("2025-06-01"), pd.Timestamp("2025-08-31"), 1000]],  # 19店がこの3か月だけ千円で入力していた（店に確認）
    columns=["店番", "開始", "終了", "倍率"])
EMPTY_FIX_STORE = REF_FIX_STORE_CODE.iloc[0:0]
EMPTY_FIX_WASTE = REF_FIX_WASTE_UNIT.iloc[0:0]


def load_dims():
    st = pd.read_csv(TRUTH / "dim_store.csv", parse_dates=["open_date", "close_date"])
    ca = pd.read_csv(TRUTH / "dim_category.csv")
    dd = pd.read_csv(TRUTH / "dim_date.csv", parse_dates=["date"])
    return st, ca, dd


def load_raw(d=RAW):
    sv = {"店コード": str}
    r = {}
    r["pos_store_day"] = pd.read_csv(d / "pos_store_day.csv.gz", dtype=sv, parse_dates=["営業日", "送信日時"])
    r["pos_dept_day"] = pd.read_csv(d / "pos_dept_day.csv.gz", dtype=sv, parse_dates=["営業日", "送信日時"])
    r["hr_attendance"] = pd.read_csv(d / "hr_attendance.csv.gz", parse_dates=["勤務日"])
    r["waste_register"] = pd.read_csv(d / "waste_register.csv.gz", dtype=sv, parse_dates=["登録日"])
    r["acct_store_month"] = pd.read_csv(d / "acct_store_month.csv")
    r["map_store_pos"] = pd.read_csv(d / "map_store_pos.csv", dtype=sv, parse_dates=["有効開始", "有効終了"])
    r["map_store_hr"] = pd.read_csv(d / "map_store_hr.csv")
    r["map_dept"] = pd.read_csv(d / "map_dept.csv", parse_dates=["有効開始", "有効終了"])
    return r


def normalize_raw(raw):
    """02_整形.make_raw の戻り値（メモリ上）を、ファイルから読んだときと同じ型にそろえる"""
    r = {k: v.copy() for k, v in raw.items()}
    for k in ("pos_store_day", "pos_dept_day", "waste_register", "map_store_pos"):
        r[k]["店コード"] = r[k]["店コード"].astype(str)
    r["hr_attendance"]["人件費"] = r["hr_attendance"]["人件費"].astype(float)
    return r


def run_param(cutoff=None, last_day=END_DAY):
    cutoff = FAR if cutoff is None else cutoff
    return pd.DataFrame({"cutoff": [cutoff], "last_day": [last_day], "last_ym": [last_day.strftime("%Y-%m")]})


def _con(raw, param, fix_store, fix_waste):
    st, ca, dd = load_dims()
    con = duckdb.connect()
    for k, v in raw.items():
        name = k if k.startswith("map_") else "raw_" + k
        con.register("v_" + name, v); con.execute(f"CREATE TABLE {name} AS SELECT * FROM v_{name}")
    for name, v in (("ref_fix_store_code", fix_store), ("ref_fix_waste_unit", fix_waste), ("run_param", param),
                    ("dim_store", st), ("dim_category", ca), ("dim_date", dd)):
        con.register("v_" + name, v); con.execute(f"CREATE TABLE {name} AS SELECT * FROM v_{name}")
    # ref_fix_store_code の 店番 は空を含むので整数に
    con.execute('CREATE OR REPLACE TABLE ref_fix_store_code AS SELECT "店コード", "有効開始", "有効終了", CAST("店番" AS INTEGER) AS "店番", "処理" FROM ref_fix_store_code')
    return con


def _run_sql_file(con, path):
    for stmt in [s.strip() for s in path.read_text(encoding="utf-8").split(";") if s.strip()]:
        body = "\n".join(l for l in stmt.splitlines() if not l.strip().startswith("--")).strip()
        if body:
            con.execute(body)


TEST_NAMES = []


def load_tests():
    txt = (SQL / "30_tests.sql").read_text(encoding="utf-8")
    parts = re.split(r"^-- test: ", txt, flags=re.M)[1:]
    out = []
    for p in parts:
        name, body = p.split("\n", 1)
        out.append((name.strip(), body.strip().rstrip(";")))
    return out


def run_tests(con):
    return {name: int(con.execute(q).fetchone()[0]) for name, q in load_tests()}


def sql_build(raw, cutoff=None, last_day=END_DAY, fixes=True):
    param = run_param(cutoff, last_day)
    con = _con(raw, param, REF_FIX_STORE_CODE if fixes else EMPTY_FIX_STORE, REF_FIX_WASTE_UNIT if fixes else EMPTY_FIX_WASTE)
    _run_sql_file(con, SQL / "10_staging.sql")
    _run_sql_file(con, SQL / "20_mart.sql")
    con.execute(f"DELETE FROM mart_fact_store_day WHERE biz_date > DATE '{last_day.date()}'")
    con.execute(f"DELETE FROM mart_fact_store_day_dept WHERE biz_date > DATE '{last_day.date()}'")
    con.execute(f"DELETE FROM mart_store_month WHERE ym > '{last_day.strftime('%Y-%m')}'")
    return con


# ---------------- pandas 版（手当てを1つずつ抜けるように）----------------
DEFAULT = dict(dedupe=True, cutoff=None, close_day=None, s16_fix=True, last_day=END_DAY, store_map="validity", fixes=True, dept_map=True, hr="mean", waste_fix=True)


def _codes(raw, fixes, s16_fix=True):
    c = raw["map_store_pos"].assign(処理="map")
    if fixes:
        f = REF_FIX_STORE_CODE if s16_fix else REF_FIX_STORE_CODE[REF_FIX_STORE_CODE["店コード"] != "1020"]
        c = pd.concat([c, f], ignore_index=True)
    return c


def _arrived(df, cutoff, close_day):
    """cutoff：この時点までに届いた行。close_day：営業日の翌月 close_day 日の24時までに届いた行（月ごとの締め）"""
    df = df[df["送信日時"] <= cutoff]
    if close_day is not None:
        lim = df["営業日"].dt.to_period("M").dt.to_timestamp(how="end").dt.normalize() + pd.Timedelta(days=close_day + 1)
        df = df[df["送信日時"] < lim]
    return df


def _map_store(df, date_col, codes, mode):
    m = df.merge(codes, on="店コード", how="inner")
    if mode == "validity":
        m = m[(m[date_col] >= m["有効開始"]) & (m[date_col] <= m["有効終了"])]
    elif mode == "oldmaster":   # 期間を見ずに、最初に作った対応表（古いコード）のつもりで1対1に引く
        first = codes.sort_values("有効開始").drop_duplicates("店コード", keep="first")
        m = df.merge(first, on="店コード", how="inner")
    elif mode == "fanout":      # 期間を見ずに結合する（同じコードの行が2つに増える）
        pass
    m = m[m["処理"] == "map"].copy()
    m["store_id"] = m["店番"].astype(int)
    return m.drop(columns=["有効開始", "有効終了", "店番", "処理"])


def _map_dept(df, date_col, mp, use):
    if not use:
        return df.assign(category_id=df["部門コード"].astype(int))
    m = df.merge(mp, on="部門コード", how="inner")
    m = m[(m[date_col] >= m["有効開始"]) & (m[date_col] <= m["有効終了"])].copy()
    m["category_id"] = m["部門番号"].astype(int)
    return m


def build_mart_pd(raw, **kw):
    o = dict(DEFAULT); o.update(kw)
    st, ca, dd = load_dims()
    cutoff = FAR if o["cutoff"] is None else o["cutoff"]
    codes = _codes(raw, o["fixes"], o["s16_fix"])

    ps = _arrived(raw["pos_store_day"], cutoff, o["close_day"])
    if o["dedupe"]:
        ps = ps.sort_values("送信日時").drop_duplicates(["店コード", "営業日"], keep="last")
    ps = _map_store(ps, "営業日", codes, o["store_map"])
    fsd = ps.rename(columns={"営業日": "biz_date", "レシート枚数": "receipts", "会員レシート枚数": "member_receipts",
                             "点数": "items", "売上金額": "sales"})[["biz_date", "store_id", "receipts", "member_receipts", "items", "sales"]]

    pdp = _arrived(raw["pos_dept_day"], cutoff, o["close_day"])
    if o["dedupe"]:
        pdp = pdp.sort_values("送信日時").drop_duplicates(["店コード", "営業日", "部門コード"], keep="last")
    pdp = _map_dept(_map_store(pdp, "営業日", codes, o["store_map"]), "営業日", raw["map_dept"], o["dept_map"])
    dept = pdp.groupby(["営業日", "store_id", "category_id"], as_index=False).agg(sales=("売上金額", "sum"), gross_profit_before_waste=("粗利金額", "sum"))

    w = _map_dept(_map_store(raw["waste_register"], "登録日", codes, o["store_map"]), "登録日", raw["map_dept"], o["dept_map"])
    w["waste"] = w["廃棄金額"].astype(float)
    if o["waste_fix"] and o["fixes"]:
        for _, f in REF_FIX_WASTE_UNIT.iterrows():
            k = (w.store_id == f["店番"]) & (w["登録日"] >= f["開始"]) & (w["登録日"] <= f["終了"])
            w.loc[k, "waste"] = w.loc[k, "waste"] * f["倍率"]
    wg = w.groupby(["登録日", "store_id", "category_id"], as_index=False).waste.sum().rename(columns={"登録日": "営業日"})
    dept = dept.merge(wg, on=["営業日", "store_id", "category_id"], how="left").fillna({"waste": 0}).rename(columns={"営業日": "biz_date"})

    hr = raw["hr_attendance"].merge(raw["map_store_hr"], on="勤怠店番").rename(columns={"勤務日": "biz_date", "店番": "store_id", "人時": "labor_hours", "人件費": "labor_cost"})
    hr = hr.merge(dd[["date", "ym", "dow"]].rename(columns={"date": "biz_date"}), on="biz_date")
    hr["labor_imputed"] = hr.labor_hours.isna().astype(int)
    if o["hr"] in ("mean", "median"):
        f = hr.dropna(subset=["labor_hours"]).groupby(["store_id", "ym", "dow"]).labor_hours.agg(o["hr"]).rename("fill")
        wg2 = hr.dropna(subset=["labor_hours"]).groupby(["store_id", "ym"])[["labor_cost", "labor_hours"]].sum()
        wage = (wg2.labor_cost / wg2.labor_hours).rename("wage")
        hr = hr.merge(f, on=["store_id", "ym", "dow"], how="left").merge(wage, on=["store_id", "ym"], how="left")
        hr["labor_hours"] = hr.labor_hours.fillna(hr["fill"])
        hr["labor_cost"] = hr.labor_cost.fillna(hr["fill"] * hr["wage"])
    elif o["hr"] == "zero":
        hr[["labor_hours", "labor_cost"]] = hr[["labor_hours", "labor_cost"]].fillna(0)
    hr = hr[["biz_date", "store_id", "labor_hours", "labor_cost", "labor_imputed"]]

    g = dept.groupby(["biz_date", "store_id"], as_index=False).agg(gross_profit_before_waste=("gross_profit_before_waste", "sum"), waste=("waste", "sum"), dept_sales=("sales", "sum"))
    fsd = fsd.merge(g, on=["biz_date", "store_id"], how="left").merge(hr, on=["biz_date", "store_id"], how="left")
    if o["hr"] == "dropday":   # 人時が空の日は、その店×日ごと落とす
        fsd = fsd[fsd.labor_imputed != 1]
    fsd["gross_profit"] = fsd.gross_profit_before_waste - fsd.waste
    fsd["labor_imputed"] = fsd.labor_imputed.fillna(0).astype(int)
    fsd = fsd[fsd.biz_date <= o["last_day"]]
    dept = dept[dept.biz_date <= o["last_day"]]

    sm = store_month(fsd, raw["acct_store_month"], st, dd)
    sm = sm[sm.ym <= o["last_day"].strftime("%Y-%m")]
    return {"mart_fact_store_day": fsd.reset_index(drop=True), "mart_fact_store_day_dept": dept.reset_index(drop=True), "mart_store_month": sm.reset_index(drop=True)}


def store_month(fsd, acct, st, dd):
    m = fsd.merge(dd[["date", "ym", "fy"]].rename(columns={"date": "biz_date"}), on="biz_date")
    S = ["sales", "receipts", "member_receipts", "items", "gross_profit_before_waste", "waste", "gross_profit", "labor_hours", "labor_cost"]
    sm = m.groupby(["ym", "fy", "store_id"], as_index=False).agg(days_with_sales=("sales", "size"), **{c: (c, "sum") for c in S}, labor_imputed_days=("labor_imputed", "sum"))
    a = acct.rename(columns={"店番": "store_id", "年月": "ym", "その他経費": "other_cost"})[["store_id", "ym", "other_cost"]]
    sm = sm.merge(a, on=["store_id", "ym"], how="left")
    sm["operating_profit"] = sm.gross_profit - sm.labor_cost - sm.other_cost
    s = st.set_index("store_id")
    ym = pd.PeriodIndex(sm.ym, freq="M")
    od = s.reindex(sm.store_id).open_date
    cd = s.reindex(sm.store_id).close_date
    age = np.array([(y - pd.Period(o, "M")).n if pd.notna(o) else -1 for y, o in zip(ym, od)])
    mend = ym.to_timestamp(how="end").normalize()
    sm["is_existing"] = ((age >= 13) & (cd.isna().values | (cd.values >= mend.values))).astype(int)
    return sm


def tests_on_pd(mart, raw, fix_store=None, cutoff=None, last_day=END_DAY):
    """pandas で作った mart を DuckDB に入れて、同じ SQL のテストを流す（fix_store：使った店コードの補正表）"""
    param = run_param(cutoff, last_day)
    con = _con(raw, param, REF_FIX_STORE_CODE if fix_store is None else fix_store, EMPTY_FIX_WASTE)
    # q_pos_unmapped は届いたファイルと対応表だけで決まる
    con.execute("""CREATE TABLE stg_store_code AS SELECT "店コード" AS pos_code, "有効開始" AS valid_from, "有効終了" AS valid_to, "店番" AS store_id, 'map' AS action FROM map_store_pos
                   UNION ALL SELECT "店コード","有効開始","有効終了","店番","処理" FROM ref_fix_store_code""")
    con.execute("""CREATE TABLE q_pos_unmapped AS SELECT p."店コード" FROM raw_pos_store_day p LEFT JOIN stg_store_code c
                   ON c.pos_code=p."店コード" AND p."営業日" BETWEEN c.valid_from AND c.valid_to WHERE c.pos_code IS NULL""")
    for k, v in mart.items():
        con.register("v_" + k, v); con.execute(f"CREATE TABLE {k} AS SELECT * FROM v_{k}")
    return run_tests(con)


if __name__ == "__main__":
    MART.mkdir(exist_ok=True); RES.mkdir(exist_ok=True)
    raw = load_raw()
    out = {}
    # 1回目：補正表なし
    con1 = sql_build(raw, fixes=False)
    out["run1_補正表なし"] = run_tests(con1)
    unm = con1.execute("SELECT pos_code, MIN(biz_date) AS first_day, MAX(biz_date) AS last_day, COUNT(*) AS n, SUM(sales) AS sales FROM q_pos_unmapped GROUP BY pos_code ORDER BY pos_code").df()
    unm.to_csv(RES / "A_run1_unmapped_codes.csv", index=False, encoding="utf-8-sig")
    w = con1.execute("SELECT store_id, ym, sales, waste, waste / sales AS waste_rate FROM mart_store_month WHERE waste < 0.005 * sales OR waste > 0.06 * sales ORDER BY store_id, ym").df()
    w.to_csv(RES / "A_run1_waste_range.csv", index=False, encoding="utf-8-sig")
    # 2回目：補正表あり
    con2 = sql_build(raw, fixes=True)
    out["run2_補正表あり"] = run_tests(con2)
    t = pd.DataFrame(out); t.index.name = "テスト"; t.to_csv(RES / "A_tests_run1_run2.csv", encoding="utf-8-sig")
    print(t)

    # SQL 版と pandas 版の一致
    sq = {k: con2.execute(f"SELECT * FROM {k}").df() for k in ("mart_fact_store_day", "mart_fact_store_day_dept", "mart_store_month")}
    pdm = build_mart_pd(raw)
    rows = []
    for k, key in (("mart_fact_store_day", ["biz_date", "store_id"]), ("mart_fact_store_day_dept", ["biz_date", "store_id", "category_id"]), ("mart_store_month", ["ym", "store_id"])):
        a = sq[k].copy(); b = pdm[k].copy()
        a["biz_date" if "biz_date" in a else "ym"] = a["biz_date" if "biz_date" in a else "ym"]
        if "biz_date" in a: a["biz_date"] = pd.to_datetime(a.biz_date); b["biz_date"] = pd.to_datetime(b.biz_date)
        j = a.merge(b, on=key, suffixes=("_sql", "_pd"), how="outer", indicator=True)
        num = [c for c in b.columns if c not in key and c not in ("fy",) and pd.api.types.is_numeric_dtype(b[c])]
        md = max(float((j[c + "_sql"].astype(float) - j[c + "_pd"].astype(float)).abs().max()) for c in num)
        rows.append({"table": k, "rows_sql": len(a), "rows_pd": len(b), "only_one_side": int((j._merge != "both").sum()), "max_abs_diff": md})
    pd.DataFrame(rows).to_csv(RES / "C_sql_vs_pandas.csv", index=False, encoding="utf-8-sig")
    print(pd.DataFrame(rows))

    # mart の書き出し（F248・F249 が使う）
    st, ca, dd = load_dims()
    f = sq["mart_fact_store_day"].sort_values(["biz_date", "store_id"])
    f.drop(columns=["dept_sales"]).to_csv(MART / "fact_store_day.csv.gz", index=False, encoding="utf-8", float_format="%.1f", date_format="%Y-%m-%d")
    sq["mart_fact_store_day_dept"].sort_values(["biz_date", "store_id", "category_id"]).to_csv(MART / "fact_store_day_category.csv.gz", index=False, encoding="utf-8", float_format="%.1f", date_format="%Y-%m-%d")
    smo = sq["mart_store_month"].sort_values(["ym", "store_id"])
    smo.to_csv(MART / "store_month.csv", index=False, encoding="utf-8-sig", float_format="%.1f")
    st.to_csv(MART / "dim_store.csv", index=False, encoding="utf-8-sig", date_format="%Y-%m-%d")
    ca.to_csv(MART / "dim_category.csv", index=False, encoding="utf-8-sig")
    dd.to_csv(MART / "dim_date.csv", index=False, encoding="utf-8-sig", date_format="%Y-%m-%d")
    con2.execute("SELECT pos_code, valid_from, valid_to, store_id, action FROM stg_store_code ORDER BY store_id, valid_from").df().to_csv(MART / "dim_store_code_history.csv", index=False, encoding="utf-8-sig", date_format="%Y-%m-%d")
    for nm in ("fact_member_month.csv", "fact_ec_day.csv"):
        pd.read_csv(TRUTH / nm).to_csv(MART / nm, index=False, encoding="utf-8-sig")
    REF_FIX_STORE_CODE.to_csv(SQL / "ref_fix_store_code.csv", index=False, encoding="utf-8-sig", date_format="%Y-%m-%d")
    REF_FIX_WASTE_UNIT.to_csv(SQL / "ref_fix_waste_unit.csv", index=False, encoding="utf-8-sig", date_format="%Y-%m-%d")
    json.dump(out, open(RES / "A_tests.json", "w"), ensure_ascii=False, indent=1)

"""02 整形：F247 の mart（または F246 の gen(seed) が返す表）を、分析用の「店×日」「店×日×部門」にそろえる。

- 03_分析.py はこのファイルの関数を読み込んで使う。直接実行すると mart から作った表の形を確かめて、results/02_check.json に書く。
- 既存店の決めごと（F246 の会社設定書）：その月の月初で開店から13か月以上、かつその月の末日まで営業している店。
"""
import importlib.util, json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
MART = ROOT / "data" / "mart"
F246 = ROOT / "data" / "f246" / "src" / "02_整形.py"


def load_gen_module():
    """F246 の合成のコード（gen(seed)）を読み込む。入力は data/f246/data/raw/ を見る。"""
    s = importlib.util.spec_from_file_location("f246gen", F246)
    g = importlib.util.module_from_spec(s); s.loader.exec_module(g)
    return g


def dims():
    st = pd.read_csv(MART / "dim_store.csv", encoding="utf-8-sig", parse_dates=["open_date", "close_date"])
    cat = pd.read_csv(MART / "dim_category.csv", encoding="utf-8-sig")
    dd = pd.read_csv(MART / "dim_date.csv", encoding="utf-8-sig", parse_dates=["date"])
    return st, cat, dd


def existing_flags(st, months):
    """店×月の既存店フラグ（会社設定書の決めごと）。"""
    rows = []
    for ym in months:
        p = pd.Period(ym, "M"); start, end = p.start_time.normalize(), p.end_time.normalize()
        for _, s in st.iterrows():
            ok = (s.open_date + pd.DateOffset(months=13) <= start) and (pd.isna(s.close_date) or s.close_date >= end)
            rows.append((ym, s.store_id, int(ok)))
    return pd.DataFrame(rows, columns=["ym", "store_id", "is_existing"])


def from_mart():
    sd = pd.read_csv(MART / "fact_store_day.csv.gz", parse_dates=["biz_date"]).rename(columns={"biz_date": "date"})
    sdc = pd.read_csv(MART / "fact_store_day_category.csv.gz", parse_dates=["biz_date"]).rename(columns={"biz_date": "date"})
    return tidy(sd, sdc)


def from_gen(g, seed):
    cal, fsd, fsdc, fmm, ec = g.gen(seed)
    return tidy(fsd[["date", "store_id", "receipts", "items", "sales"]].copy(), fsdc.copy())


def tidy(sd, sdc):
    st, cat, dd = dims()
    sd = sd[["date", "store_id", "receipts", "items", "sales"]].copy()
    sd["date"] = pd.to_datetime(sd.date)
    sd = sd.merge(dd[["date", "ym", "dow", "hol"]], on="date").merge(st[["store_id", "area"]], on="store_id")
    sdc = sdc[["date", "store_id", "category_id", "sales"]].copy()
    sdc["date"] = pd.to_datetime(sdc.date)
    sdc["ym"] = sdc.date.dt.strftime("%Y-%m")
    return sd, sdc


if __name__ == "__main__":
    st, cat, dd = dims()
    sd, sdc = from_mart()
    sm = pd.read_csv(MART / "store_month.csv", encoding="utf-8-sig")
    ex = existing_flags(st, sorted(sm.ym.unique()))
    chk = sm[["ym", "store_id", "is_existing"]].merge(ex, on=["ym", "store_id"], suffixes=("_mart", "_rule"))
    out = {"store_day_rows": len(sd), "store_day_category_rows": len(sdc),
           "existing_flag_mismatch": int((chk.is_existing_mart != chk.is_existing_rule).sum()),
           "sales_total_diff_day_vs_category": float(sd.sales.sum() - sdc.sales.sum())}
    (ROOT / "results").mkdir(exist_ok=True)
    json.dump(out, open(ROOT / "results" / "02_check.json", "w"), ensure_ascii=False, indent=1)
    print(out)

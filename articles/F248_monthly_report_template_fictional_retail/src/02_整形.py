"""02 整形：月次レポートの材料を作る。

1. 締めの日ごとの店×月（data/versions/store_month_d{1,3,5,10}.csv）
   F247 の build_mart_pd(raw, close_day=k) で「翌月 k 日の24時までに届いた POS だけ」で作った店×月。
   確定版は F247 の mart/store_month.csv（data/in/）。遅れて届くのは POS（売上・客数・点数・粗利）だけで、廃棄・勤怠・会計は締めの時点でそろっている設定（F247 と同じ）。
   ※ F247 のフォルダ（../F247_data_mart_fictional_retail）で F247 の 01〜03 を先に流しておく必要がある。
2. FY2025 の計画（予算）（data/plan_fy2025.csv）
   架空の経営企画が 2025年3月に作った、という設定の合成の計画。FY2024 の同じ月の実績をもとに、
   売上 +3.0%（客数 ±0、単価 +3%）、粗利率（廃棄後）は前年と同じ、人件費 +3.0%、その他の経費 +2.0% と置いた。
   前年同月の実績がない店×月（08店の 2025-04〜09、16店の全月）は、同じ地域・同じ大きさの店の前年同月の平均 × 0.9 とした。
   24店は 2025-09 末の閉店を織り込み、10月以降の計画はない。
会社・数字はすべて架空（合成データ）。
"""
import importlib.util, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
F247 = ROOT.parent / "F247_data_mart_fictional_retail"
PLAN_G = dict(sales=0.03, labor=0.03, other=0.02, new_store_factor=0.9)


def load_f247():
    s = importlib.util.spec_from_file_location("f247", F247 / "src" / "03_整える.py")
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
    return m


def make_versions(close_days=(1, 3, 5, 10)):
    M = load_f247()
    raw = M.load_raw()
    (DATA / "versions").mkdir(exist_ok=True)
    cols = pd.read_csv(DATA / "in" / "store_month.csv", nrows=1).columns
    for cd in close_days:
        sm = M.build_mart_pd(raw, close_day=cd)["mart_store_month"][list(cols)]
        sm.to_csv(DATA / "versions" / f"store_month_d{cd}.csv", index=False, encoding="utf-8-sig")
        print("close day", cd, len(sm), round(sm[sm.fy == 2025].sales.sum() / 1e8, 2), "億円")


def make_plan(sm, st, g=PLAN_G):
    """FY2025 の店×月の計画。sm は確定版の店×月"""
    prev = sm[sm.fy == 2024].copy()
    prev["ym25"] = (pd.PeriodIndex(prev.ym, freq="M") + 12).strftime("%Y-%m")
    stx = st.set_index("store_id")
    months = pd.period_range("2025-04", "2026-03", freq="M").strftime("%Y-%m")
    rows = []
    for sid in st.store_id:
        o, c = stx.loc[sid, "open_date"], stx.loc[sid, "close_date"]
        for ym in months:
            p = pd.Period(ym, "M")
            if pd.Timestamp(o) > p.to_timestamp(how="end") or (pd.notna(c) and pd.Timestamp(c) < p.to_timestamp()):
                continue
            base = prev[(prev.store_id == sid) & (prev.ym25 == ym)]
            f = 1.0
            if len(base) == 0 or base.days_with_sales.iloc[0] < p.days_in_month:
                peers = stx[(stx.area == stx.loc[sid, "area"]) & (stx["size"] == stx.loc[sid, "size"]) & (stx.index != sid)].index
                base = prev[(prev.store_id.isin(peers)) & (prev.ym25 == ym) & (prev.days_with_sales == p.days_in_month)]
                f = g["new_store_factor"]
            b = base[["sales", "gross_profit", "labor_cost", "other_cost"]].mean() * f
            gpr = b.gross_profit / b.sales
            ps = b.sales * (1 + g["sales"])
            rows.append({"ym": ym, "store_id": sid, "plan_sales": ps, "plan_gross_profit": ps * gpr,
                         "plan_labor_cost": b.labor_cost * (1 + g["labor"]), "plan_other_cost": b.other_cost * (1 + g["other"])})
    pl = pd.DataFrame(rows)
    pl["plan_operating_profit"] = pl.plan_gross_profit - pl.plan_labor_cost - pl.plan_other_cost
    return pl


if __name__ == "__main__":
    sm = pd.read_csv(DATA / "in" / "store_month.csv")
    st = pd.read_csv(DATA / "in" / "dim_store.csv", parse_dates=["open_date", "close_date"])
    pl = make_plan(sm, st)
    pl.round(0).to_csv(DATA / "plan_fy2025.csv", index=False, encoding="utf-8-sig")
    t = pl.sum(numeric_only=True)
    print("plan FY2025: sales %.1f 億円, OP %.2f 億円" % (t.plan_sales / 1e8, t.plan_operating_profit / 1e8))
    make_versions()

"""02 整形：F247 の mart から、Power BI に読ませるスタースキーマ（powerbi/data/）を作る。

- 会社・数字は架空（サンプルマート（架空）、合成データ）。
- 事実テーブル：fact_store_day（店×日）、fact_store_day_category（店×日×部門）、fact_store_month（店×月：その他の経費・既存店の印）、
  fact_member_month（店×月：会員）。次元：dim_date・dim_store・dim_category。ほかに ref_noise_band（偶然の幅）と sec_user_area（RLS 用）。
- 月の表は month_start（その月の1日）で dim_date[date] につなぐ。
- dim_date[day_weight]：曜日・祝日の並びの重み（F246 と同じ作り方。ただし客数ではなく、売上の「1店あたり・1日」で作る）。
"""
import pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
IN = ROOT / "data" / "in" / "mart"
OUT = ROOT / "powerbi" / "data"; OUT.mkdir(parents=True, exist_ok=True)
F246 = ROOT / "data" / "in" / "f246"
DOW_JA = ["月", "火", "水", "木", "金", "土", "日"]


def rd(name):
    return pd.read_csv(IN / name, encoding="utf-8-sig")


def build():
    dd = rd("dim_date.csv"); st = rd("dim_store.csv"); cat = rd("dim_category.csv")
    fsd = rd("fact_store_day.csv.gz"); fsdc = rd("fact_store_day_category.csv.gz")
    sm = rd("store_month.csv"); fmm = rd("fact_member_month.csv")
    for d in (dd,):
        d["hol"] = d.hol.astype(str).str.lower().eq("true"); d["flyer"] = d.flyer.astype(str).str.lower().eq("true")

    # 曜日・祝日の重み（売上／営業店数の平均。祝日は平日の祝日だけ倍率をかける）
    daily = fsd.groupby("biz_date").agg(sales=("sales", "sum"), n=("store_id", "nunique")).reset_index()
    daily = daily.merge(dd.rename(columns={"date": "biz_date"}), on="biz_date")
    daily["sps"] = daily.sales / daily.n
    # 季節と物価の流れを外すため、その月の平均で割ってから曜日の平均をとる
    daily["rel"] = daily.sps / daily.groupby("ym").sps.transform("mean")
    w_dow = daily.groupby("dow").rel.mean(); w_dow = w_dow / w_dow.mean()
    wk = daily[daily.dow < 5]
    hol_mult = wk[wk.hol].rel.mean() / wk[~wk.hol].rel.mean()
    dd["day_weight"] = w_dow.reindex(dd.dow).values * np.where(dd.hol & (dd.dow < 5), hol_mult, 1.0)

    dd["hol"] = dd.hol.astype(int); dd["flyer"] = dd.flyer.astype(int)  # Power Query で読みやすいよう 0/1 に
    dd["month_start"] = dd.ym + "-01"
    dd["fy_label"] = "FY" + dd.fy.astype(str)
    m = pd.to_datetime(dd.date).dt.month
    dd["fy_month_no"] = np.where(m >= 4, m - 3, m + 9)
    dd["dow_name"] = [DOW_JA[i] for i in dd.dow]
    dd["year"] = pd.to_datetime(dd.date).dt.year; dd["month"] = m
    dim_date = dd[["date", "year", "month", "ym", "month_start", "fy", "fy_label", "fy_month_no", "dow", "dow_name", "hol", "flyer", "day_weight"]]

    dim_store = st.copy()
    dim_store["area_order"] = dim_store.area.map({"都市": 1, "郊外": 2, "地方": 3})

    f_day = fsd.copy()
    f_month = sm[["ym", "store_id", "other_cost", "is_existing", "labor_imputed_days", "days_with_sales"]].copy()
    f_month.insert(0, "month_start", f_month.ym + "-01"); f_month = f_month.drop(columns="ym")
    f_mem = fmm.copy(); f_mem.insert(0, "month_start", f_mem.ym + "-01"); f_mem = f_mem.drop(columns="ym")

    # 偶然の幅（F246 の results/C_noise_by_grain.csv から写す。1.96σ、単位 % または pt）
    nz = pd.read_csv(ROOT.parent / "F246_kpi_definitions_fictional_retail" / "results" / "C_noise_by_grain.csv", encoding="utf-8-sig") \
        if (ROOT.parent / "F246_kpi_definitions_fictional_retail").exists() else \
        pd.read_csv("https://raw.githubusercontent.com/takayuki-0127/japan-open-data-notes/3006b82/articles/F246_kpi_definitions_fictional_retail/results/C_noise_by_grain.csv", encoding="utf-8-sig")
    nz = nz.rename(columns={"偶然の幅（±1.96σ）": "band", "単位": "unit"})[["level", "grain", "KPI", "band", "unit"]]
    nz["band_ratio"] = nz.band / 100  # % も pt も 1/100 にして、DAX では比（0.064 など）で使う

    sec = pd.DataFrame({"user_principal": ["area.toshi@example.com", "area.kogai@example.com", "area.chiho@example.com", "hq.planning@example.com",
                                           "hq.planning@example.com", "hq.planning@example.com"],
                        "area": ["都市", "郊外", "地方", "都市", "郊外", "地方"]})

    out = {"dim_date.csv": dim_date, "dim_store.csv": dim_store, "dim_category.csv": cat,
           "fact_store_day.csv.gz": f_day, "fact_store_day_category.csv.gz": fsdc,
           "fact_store_month.csv": f_month, "fact_member_month.csv": f_mem,
           "ref_noise_band.csv": nz, "sec_user_area.csv": sec}
    for k, v in out.items():
        v.to_csv(OUT / k, index=False, encoding="utf-8-sig")
        print(f"{k:34s} {len(v):>7,d} 行  {(OUT / k).stat().st_size:>10,d} bytes")
    pd.DataFrame({"dow": range(7), "dow_name": DOW_JA, "weight": w_dow.values}).assign(hol_mult=hol_mult) \
        .to_csv(ROOT / "results" / "A_day_weight.csv", index=False, encoding="utf-8-sig")
    print("曜日の重み", w_dow.round(3).tolist(), "平日の祝日の倍率", round(hol_mult, 3))


if __name__ == "__main__":
    build()

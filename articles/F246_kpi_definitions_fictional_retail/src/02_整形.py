"""02 整形（合成）：架空の小売チェーン「サンプルマート（架空）」の4年分のデータを作る。

- 実在の会社のデータではない。売上の季節・物価の動きだけを公開データ（商業動態統計のスーパー、家計調査の食品価格）から借り、
  店・客・商品・人時はすべて乱数で合成する（会社の設定は docs/company_spec.md）。
- 期間は 2022-04-01〜2026-03-31（4会計年度、FY2022〜FY2025。4月始まり）。
- gen(seed) は同じ設定で乱数の種だけを変えたデータを返す（03_分析.py の「ばらつき」の確認で使う）。
- 出力（seed=0）：data/ に dim_store, dim_category, dim_date, fact_store_day, fact_store_day_category, fact_member_month, fact_ec_day
"""
import pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
START, END = "2022-04-01", "2026-03-31"

CATS = pd.DataFrame({
    "category_id": [1, 2, 3, 4, 5, 6, 7],
    "category": ["青果", "精肉", "鮮魚", "惣菜", "日配", "加工食品", "日用品"],
    "share": [0.13, 0.12, 0.08, 0.11, 0.20, 0.26, 0.10],
    "margin": [0.26, 0.27, 0.28, 0.40, 0.25, 0.22, 0.20],   # 値入れ後の粗利率（廃棄前）
    "waste": [0.030, 0.020, 0.050, 0.060, 0.015, 0.003, 0.000],  # 売上に対する廃棄・値引きロス
    "promo": [1, 1, 1, 0, 1, 0, 1],  # チラシの対象になりやすい部門
})

# 店：24店（開店2・閉店2を含む）。area: 都市・郊外・地方、size: S/M/L
STORES = pd.DataFrame({
    "store_id": range(1, 25),
    "area": ["都市"] * 8 + ["郊外"] * 8 + ["地方"] * 8,
    "size": ["L", "M", "M", "S", "S", "M", "L", "S",
             "L", "M", "M", "M", "S", "L", "M", "S",
             "M", "S", "S", "M", "S", "M", "L", "S"],
})
STORES["open_date"] = pd.Timestamp("2010-04-01")
STORES["close_date"] = pd.NaT
# 開店：都市に1店（2024-10）、郊外に1店（2025-04）。閉店：地方の2店（2024-09末、2025-09末）
STORES.loc[STORES.store_id == 8, "open_date"] = pd.Timestamp("2024-10-01")
STORES.loc[STORES.store_id == 16, "open_date"] = pd.Timestamp("2025-04-01")
STORES.loc[STORES.store_id == 21, "close_date"] = pd.Timestamp("2024-09-30")
STORES.loc[STORES.store_id == 24, "close_date"] = pd.Timestamp("2025-09-30")
STORES["store_name"] = [f"サンプルマート{a}{i:02d}店（架空）" for a, i in zip(STORES.area, STORES.store_id)]

BASE_REC = {"S": 900, "M": 1400, "L": 2000}
AREA_TREND = {"都市": 0.012, "郊外": 0.000, "地方": -0.025}      # 客数の年あたりの流れ
AREA_ITEMS = {"都市": 8.6, "郊外": 9.6, "地方": 10.4}             # 1回あたりの買上点数
AREA_PRICE = {"都市": 1.06, "郊外": 1.00, "地方": 0.95}           # 一品単価の水準
DOW = np.array([0.95, 0.93, 1.02, 0.96, 1.00, 1.14, 1.10])        # 月〜日
LABOR_BASE = {"S": 140, "M": 200, "L": 260}


def _dates():
    cal = pd.read_csv(RAW / "calendar_daily.csv.gz", parse_dates=["date"])
    cal = cal[(cal.date >= START) & (cal.date <= END)].reset_index(drop=True)
    cal["ym"] = cal.date.dt.strftime("%Y-%m")
    cal["fy"] = np.where(cal.date.dt.month >= 4, cal.date.dt.year, cal.date.dt.year - 1)
    cal["flyer"] = cal.dow.isin([2, 5])  # 水曜・土曜にチラシ
    return cal


def _indices(cal):
    """公開データから借りる2つの動き：①売上の月ごとの形（スーパー販売額）②一品単価の上がり方（家計調査の食品価格）"""
    s = pd.read_csv(RAW / "sales_monthly_6types.csv")
    s = s[(s["業態"] == "スーパー") & (s["品目"] == "合計")].set_index("ym")["販売額_百万円"]
    days = pd.Series({ym: pd.Period(ym).days_in_month for ym in s.index})
    per_day = s / days
    k = pd.read_csv(RAW / "kakei_items.csv").sort_values(["code", "year"])
    k["dl"] = np.log(k.price).groupby(k.code).diff()
    k = k.dropna(subset=["dl"])
    yr = k.groupby("year")[["dl", "exp"]].apply(lambda d: np.average(d.dl, weights=d.exp))
    pidx = np.exp(yr.loc[2022:].cumsum())
    pidx = pidx / pidx.loc[2022]
    # 2025・2026年は家計調査がまだないので、年+4%と置く（仮定）
    pidx.loc[2025] = pidx.loc[2024] * 1.04
    pidx.loc[2026] = pidx.loc[2025] * 1.04
    # 年の値を月に直線で補間（年の値を7月に置く）
    anchor = pd.Series(pidx.values, index=pd.to_datetime([f"{y}-07-01" for y in pidx.index]))
    mon = pd.date_range("2022-01-01", "2026-12-01", freq="MS")
    pm = anchor.reindex(anchor.index.union(mon)).interpolate("time").bfill().ffill().reindex(mon)
    pm.index = pm.index.strftime("%Y-%m")
    sales_m = per_day.reindex(cal.ym.unique())
    # 2026年9月以降はないが、期間は2026-03までなので足りる
    vol = sales_m / pm.reindex(sales_m.index)
    vol = vol / vol.loc["2022-04":"2023-03"].mean()   # 客数×点数の月ごとの形（季節を含む）
    return pm, vol


def gen(seed=0):
    rng = np.random.default_rng(seed)
    cal = _dates()
    pm, vol = _indices(cal)
    nd, ns = len(cal), len(STORES)
    t_year = ((cal.date - pd.Timestamp(START)).dt.days / 365.25).values
    dow = DOW[cal.dow.values]
    hol = np.where(cal.hol.values & (cal.dow.values < 5), 1.07, 1.0)
    year_end = np.where((cal.date.dt.month == 12) & (cal.date.dt.day >= 28), 1.35, 1.0)
    flyer = np.where(cal.flyer.values, 1.07, 1.0)
    volm = vol.reindex(cal.ym).values
    pmd = pm.reindex(cal.ym).values

    rows = []
    store_re = rng.normal(0, 0.04, ns)                      # 店ごとの水準のずれ
    store_month = rng.normal(0, 0.02, (ns, cal.ym.nunique()))  # 店×月のずれ
    ym_codes = pd.factorize(cal.ym)[0]
    for j, st in STORES.iterrows():
        open_ok = (cal.date >= st.open_date).values
        close_ok = cal.date.le(st.close_date).values if pd.notna(st.close_date) else np.ones(nd, bool)
        alive = open_ok & close_ok
        days_open = (cal.date - st.open_date).dt.days.values
        ramp = np.where(days_open < 0, 0, np.clip(0.75 + 0.25 * days_open / 180, 0.75, 1.0))
        ramp = np.where(days_open < 14, ramp * 1.30, ramp)   # 開店直後の2週間はにぎわう
        if st.open_date < pd.Timestamp(START):
            ramp = np.ones(nd)
        trend = np.exp(AREA_TREND[st.area] * t_year)
        lam = BASE_REC[st["size"]] * np.exp(store_re[j]) * trend * dow * hol * year_end * flyer * volm ** 0.85 * ramp
        lam = lam * np.exp(store_month[j, ym_codes]) * np.exp(rng.normal(0, 0.05, nd))
        receipts = rng.poisson(np.maximum(lam, 1))
        items_per = AREA_ITEMS[st.area] * (volm ** 0.15) * (pmd ** -0.25) * np.exp(rng.normal(0, 0.03, nd))
        items = np.round(receipts * items_per)
        unit_price = 228 * AREA_PRICE[st.area] * pmd * np.where(cal.flyer.values, 0.985, 1.0) * np.exp(rng.normal(0, 0.02, nd))
        sales = items * unit_price
        member_share = np.clip(0.55 + 0.025 * t_year + (0.03 if st.area == "都市" else 0), 0, 0.9)
        member_receipts = rng.binomial(receipts, member_share)
        wage = 1150 * np.exp(0.04 * t_year) * (1.08 if st.area == "都市" else 1.0)
        labor_hours = (LABOR_BASE[st["size"]] + 0.030 * receipts) * np.exp(rng.normal(0, 0.03, nd))
        df = pd.DataFrame({
            "date": cal.date, "store_id": st.store_id, "receipts": receipts, "member_receipts": member_receipts,
            "items": items, "sales": sales, "labor_hours": labor_hours, "labor_cost": labor_hours * wage,
            "other_cost": (260000 if st["size"] == "S" else 340000 if st["size"] == "M" else 460000) * np.exp(0.02 * t_year),
            "flyer": cal.flyer.values,
        })[alive]
        rows.append(df)
    fsd = pd.concat(rows, ignore_index=True)

    # 部門別：売上を部門の構成で分け、チラシの日は対象部門の粗利率を1ポイント下げる
    n = len(fsd)
    share = CATS.share.values * np.exp(rng.normal(0, 0.05, (n, len(CATS))))
    share = share / share.sum(1, keepdims=True)
    csales = fsd.sales.values[:, None] * share
    marg = CATS.margin.values[None, :] - 0.01 * (fsd.flyer.values[:, None] * CATS.promo.values[None, :])
    # 店ごとの廃棄のしやすさ（発注の上手下手）と、地方の店で FY2025 に少し悪化する流れ
    st_w = pd.Series(np.exp(rng.normal(0, 0.30, len(STORES))), index=STORES.store_id)
    rural = fsd.store_id.map(STORES.set_index("store_id").area).eq("地方").values
    fy25 = (fsd.date >= "2025-04-01").values
    wmult = st_w.reindex(fsd.store_id).values * np.where(rural & fy25, 1.25, 1.0)
    waste_r = CATS.waste.values[None, :] * wmult[:, None] * np.exp(rng.normal(0, 0.25, (n, len(CATS))))
    gp_before = csales * marg
    waste = csales * waste_r
    fsd["gross_profit_before_waste"] = gp_before.sum(1)
    fsd["waste"] = waste.sum(1)
    fsd["gross_profit"] = fsd.gross_profit_before_waste - fsd.waste
    fsdc = pd.DataFrame({
        "date": np.repeat(fsd.date.values, len(CATS)),
        "store_id": np.repeat(fsd.store_id.values, len(CATS)),
        "category_id": np.tile(CATS.category_id.values, n),
        "sales": csales.ravel(), "gross_profit_before_waste": gp_before.ravel(), "waste": waste.ravel(),
    })

    # 会員：店×月の会員の人数（重複を除いた来店者）。1人あたり月の来店回数を地域ごとに置く
    fsd["ym"] = fsd.date.dt.strftime("%Y-%m")
    mm = fsd.groupby(["store_id", "ym"], as_index=False).member_receipts.sum()
    mm = mm.merge(STORES[["store_id", "area"]], on="store_id")
    t_m = (pd.to_datetime(mm.ym) - pd.Timestamp(START)).dt.days / 365.25
    freq = np.where(mm.area == "地方", 4.6 - 0.08 * t_m, np.where(mm.area == "郊外", 4.2, 3.8 + 0.03 * t_m))
    freq = freq * np.exp(rng.normal(0, 0.02, len(mm)))
    mm["active_members"] = np.round(mm.member_receipts / freq).astype(int)
    fmm = mm[["store_id", "ym", "active_members", "member_receipts"]]

    # ネットスーパー（チェーン全体、2023-10開始）
    ec = cal[cal.date >= "2023-10-01"][["date"]].copy()
    tt = (ec.date - pd.Timestamp("2023-10-01")).dt.days.values / 365.25
    ec["orders"] = rng.poisson(120 + 160 * tt)
    ec["ec_sales"] = ec.orders * 6200 * pm.reindex(ec.date.dt.strftime("%Y-%m")).values * np.exp(rng.normal(0, 0.03, len(ec)))
    ec["delivery_cost"] = ec.orders * 650

    fsd = fsd.drop(columns=["ym"])
    return cal, fsd, fsdc, fmm, ec


def main():
    cal, fsd, fsdc, fmm, ec = gen(0)
    D = ROOT / "data"
    st = STORES.copy()
    st["open_date"] = st.open_date.dt.strftime("%Y-%m-%d")
    st["close_date"] = st.close_date.dt.strftime("%Y-%m-%d")
    st[["store_id", "store_name", "area", "size", "open_date", "close_date"]].to_csv(D / "dim_store.csv", index=False)
    CATS[["category_id", "category", "margin", "waste", "promo"]].to_csv(D / "dim_category.csv", index=False)
    dd = cal[["date", "ym", "fy", "dow", "hol", "flyer"]].copy()
    dd["date"] = dd.date.dt.strftime("%Y-%m-%d")
    dd.to_csv(D / "dim_date.csv", index=False)
    r = lambda x: x.round(0)
    f = fsd.copy(); f["date"] = f.date.dt.strftime("%Y-%m-%d")
    for c in ["sales", "labor_cost", "other_cost", "gross_profit_before_waste", "waste", "gross_profit"]:
        f[c] = r(f[c])
    f["labor_hours"] = f.labor_hours.round(1)
    f.drop(columns=["flyer"]).to_csv(D / "fact_store_day.csv.gz", index=False)
    c = fsdc.copy(); c["date"] = pd.to_datetime(c.date).dt.strftime("%Y-%m-%d")
    for k in ["sales", "gross_profit_before_waste", "waste"]:
        c[k] = r(c[k])
    c.to_csv(D / "fact_store_day_category.csv.gz", index=False)
    fmm.to_csv(D / "fact_member_month.csv", index=False)
    e = ec.copy(); e["date"] = e.date.dt.strftime("%Y-%m-%d"); e["ec_sales"] = r(e.ec_sales)
    e.to_csv(D / "fact_ec_day.csv", index=False)
    print("store-day", len(fsd), "store-day-cat", len(fsdc), "member-month", len(fmm), "ec", len(ec))


if __name__ == "__main__":
    main()

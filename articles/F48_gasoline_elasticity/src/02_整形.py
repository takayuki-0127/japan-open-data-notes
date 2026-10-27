"""月次の表を作る：販売量・価格・原油（円建て）・物価・家計調査"""
import numpy as np
import pandas as pd
from common import RAW, DATA

# 販売量（石油連盟の表、資源・エネルギー統計）
x = pd.read_excel(RAW / "paj-02_2610.xlsx", sheet_name="3.販売", header=None)
m = x[x[0].astype(str).str.match(r"^\d{4}年\d{1,2}月$")].iloc[:, [0, 1]]
m.columns = ["label", "gas_kl"]
m["month"] = pd.to_datetime(m["label"].str.replace("年", "-").str.replace("月", ""), format="%Y-%m").dt.to_period("M")
sales = m.set_index("month")["gas_kl"].astype(float)

# レギュラーの店頭価格（週次→月平均、全国）
w = pd.read_excel(RAW / "261021s5.xlsx", sheet_name="レギュラー", header=0)
w = w.iloc[:, [1, 2]]
w.columns = ["date", "price"]
w = w.dropna()
w["date"] = pd.to_datetime(w["date"])
w["price"] = pd.to_numeric(w["price"], errors="coerce")
price = w.dropna().groupby(w["date"].dt.to_period("M"))["price"].mean()

# 原油（ドバイ、ドル）とドル円
oil = pd.read_csv(RAW / "POILDUBUSDM.csv")
oil["month"] = pd.to_datetime(oil.iloc[:, 0]).dt.to_period("M")
oil = oil.set_index("month").iloc[:, -1].astype(float)
b = pd.read_csv(RAW / "boj_prices_fx.csv")
fx = b[b.series_code == "FXERM07"].copy()
fx["month"] = pd.to_datetime(fx["date"].astype(str), format="%Y%m").dt.to_period("M")
fx = fx.set_index("month")["value"].astype(float)

# 消費者物価（総合）
c = pd.read_csv(RAW / "cpi_f12.csv")
c["month"] = pd.to_datetime(c["month"]).dt.to_period("M")
cpi = c.set_index("month")["cpi_all"].astype(float)

# 家計調査 ガソリンの支出金額（円/世帯・月）
def kakei(fn):
    t = pd.read_csv(RAW / fn, header=None, dtype=str)
    years = t.iloc[1, 8:].ffill()                 # 2行目：年（12か月ごとに1つ）
    row = t[t[7] == "ガソリン"].iloc[0, 8:]
    out = {}
    for j, (y, v) in enumerate(zip(years, row)):
        if not isinstance(y, str) or not isinstance(v, str) or v in ("", "-"):
            continue
        mo = (int(t.iloc[0, 8 + j]) - 1) % 12 + 1   # 1行目：通し番号（1, 2, …）→ 月
        out[pd.Period(f"{int(y[:4])}-{mo:02d}", "M")] = float(v)
    return pd.Series(out)
hh = pd.concat([kakei(f) for f in ["kakei_000040270649.csv", "kakei_000040270650.csv", "kakei_000040270651.csv"]])
hh = hh[~hh.index.duplicated()].sort_index()

df = pd.DataFrame({"gas_kl": sales, "price": price, "oil_usd": oil, "usdjpy": fx, "cpi": cpi, "hh_yen": hh})
df.index.name = "month"
df = df.loc["2014-01":"2026-08"]
df["days"] = df.index.days_in_month
df["oil_yen_l"] = df.oil_usd * df.usdjpy / 158.987  # 1バレル=158.987ℓ。原油の円建て価格（円/ℓ）
df["rprice"] = df.price / df.cpi * 100            # 実質価格（2020年=100の物価で割る）
df["hh_l"] = df.hh_yen / df.price                  # 家計調査の支出÷価格＝1世帯当たりの購入量の目安（ℓ）
df.to_csv(DATA / "monthly.csv")
print(df.loc["2017-01":].describe().T[["count", "min", "max"]])
print(df.tail(3))

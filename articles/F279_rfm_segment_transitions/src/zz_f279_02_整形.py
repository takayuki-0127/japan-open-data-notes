"""02 整形：明細を請求書（Invoice）単位の純額にまとめる。
- 顧客IDのない行は除く
- Invoice が C で始まる行は取消：金額（負）をそのまま足して純額にする
- 取消以外で数量か価格が0以下の行は除く"""
import pathlib, pandas as pd, numpy as np
ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"; OUT = ROOT / "data" / "processed"; OUT.mkdir(parents=True, exist_ok=True)
xl = pd.read_excel(RAW / "online_retail_II.xlsx", sheet_name=None, dtype={"Invoice": str, "StockCode": str})
df = pd.concat(xl.values(), ignore_index=True)
n0 = len(df)
df = df.drop_duplicates()
n_dup = n0 - len(df)
df = df[df["Customer ID"].notna()].copy()
df["cancel"] = df["Invoice"].str.startswith("C")
bad = (~df["cancel"]) & ((df["Quantity"] <= 0) | (df["Price"] <= 0))
df = df[~bad].copy()
df["amount"] = df["Quantity"] * df["Price"]
df["cust"] = df["Customer ID"].astype(int)
inv = (df.groupby(["Invoice", "cust"], as_index=False)
         .agg(date=("InvoiceDate", "min"), amount=("amount", "sum"), cancel=("cancel", "first"), country=("Country", "first")))
inv = inv.sort_values(["date", "Invoice"]).reset_index(drop=True)
inv["date"] = inv["date"].dt.strftime("%Y-%m-%d %H:%M")
inv["amount"] = inv["amount"].round(2)
inv.to_csv(OUT / "invoices.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})
info = dict(rows_raw=n0, dup_rows=n_dup, rows_with_customer=int(len(df)), invoices=int(len(inv)),
            cancel_invoices=int(inv["cancel"].sum()), customers=int(inv["cust"].nunique()),
            first=inv["date"].min(), last=inv["date"].max())
pd.Series(info).to_json(OUT / "summary.json", force_ascii=False, indent=1)
print(info)

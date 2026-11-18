"""data/raw の Excel から、分析に使う月次の表を作る（オフライン）。
出力：data/monthly_machinery.csv（機械器具小売業の指数と販売額）、data/monthly_appliance_goods.csv（家電大型専門店の商品別）"""
import pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"


def ym_from_code(code):
    s = str(code)
    return f"{s[:4]}-{s[-2:]}"


def read_index(sheet):
    d = pd.read_excel(RAW / "meti_index_by_business.xlsx", sheet_name=sheet, header=None)
    hdr = d.iloc[6].tolist()
    col = hdr.index("機械器具小売業")
    rows = d.iloc[8:]
    rows = rows[rows[0].astype(str).str.fullmatch(r"\d{10}")]
    return pd.Series(pd.to_numeric(rows[col]).values, index=[ym_from_code(c) for c in rows[0]])


orig = read_index("原指数(Original indices)（Monthly）")
sa = read_index("季調済指数(Seasonaly adjusted)（月次M）")

s = pd.read_excel(RAW / "meti_sales_by_business.xlsx", sheet_name="販売額（value）(月次M)", header=None)
col = s.iloc[5].tolist().index("機械器具小売業")
rows = s.iloc[7:]
rows = rows[rows[0].astype(str).str.fullmatch(r"\d{10}")]
val = pd.Series(pd.to_numeric(rows[col], errors="coerce").values, index=[ym_from_code(c) for c in rows[0]])

m = pd.DataFrame({"index_orig": orig, "index_sa": sa}).join(val.rename("sales_bil_yen"), how="left")
m.index.name = "ym"
m = m.sort_index()
m.to_csv(ROOT / "data" / "monthly_machinery.csv", float_format="%.4f")

# 家電大型専門店 商品別（百万円）
a = pd.read_excel(RAW / "meti_appliance_stores.xlsx", sheet_name="販売額(value)月次(Monthly)", header=None)
names = a.iloc[5].tolist()
want = {"商品販売額": "total", "ＡＶ家電": "av", "情報家電": "info", "通信家電": "comm",
        "カメラ類": "camera", "生活家電": "living", "店舗数": "stores"}
cols = {}
for j, n in enumerate(names):
    if n in want and want[n] not in cols.values():
        cols[j] = want[n]
rows = a.iloc[7:]
rows = rows[rows[0].astype(str).str.fullmatch(r"\d{10}")]
g = pd.DataFrame({v: pd.to_numeric(rows[j], errors="coerce").values for j, v in cols.items()},
                 index=[ym_from_code(c) for c in rows[0]])
# 「その他」は生活家電のあとの最初の「その他」（生活家電の内訳の「その他」と区別する）
j_living = names.index("生活家電")
j_other = [j for j, n in enumerate(names) if n == "その他" and j > j_living]
# 生活家電の内訳（家事・調理・理美容・季節・その他）の後にある大分類の「その他」を探す
top = [j for j in j_other if str(a.iloc[6, j]).strip() == "Others"]
g["other"] = pd.to_numeric(rows[top[0]], errors="coerce").values
# 2018年の年間補正：2017年12月以前にリンク係数をかけて2018年1月以降と接続する（注1）
g = g.astype(float)
link = {"total": 0.9977, "comm": 0.9754, "stores": 0.9743}
pre = g.index < "2018-01"
for k, c in link.items():
    g.loc[pre, k] = g.loc[pre, k] * c
g.index.name = "ym"
g.to_csv(ROOT / "data" / "monthly_appliance_goods.csv", float_format="%.2f")
print("machinery", len(m), "months; appliance goods", len(g), "months")

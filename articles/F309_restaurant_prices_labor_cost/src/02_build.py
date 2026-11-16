"""CPI（CSV）と毎勤（gz）から、月次の分析用の表を作る（オフライン）。出力：data/monthly.csv"""
import gzip, io, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW, DATA = ROOT / "data" / "raw", ROOT / "data"
def cpi(name, cols):
    t = pd.read_csv(RAW / name, encoding="cp932", header=None, dtype=str)
    head = t.iloc[0].tolist()
    out = {}
    for want, key in cols.items():
        j = head.index(want)  # 最初に出てくる列
        out[key] = j
    body = t.iloc[5:]
    body = body[body[0].str.fullmatch(r"\d{6}")]
    df = pd.DataFrame({"ym": body[0].astype(int)})
    for key, j in out.items():
        df[key] = pd.to_numeric(body[j], errors="coerce").values
    return df
a = cpi("cpi_middle_class_index.csv", {"外食": "cpi_eatout", "生鮮食品を除く食料": "cpi_food_xfresh", "総合": "cpi_all"})
b = cpi("cpi_goods_services_index.csv", {"食料工業製品": "cpi_processed_food", "他のサービス": "cpi_other_services", "一般サービス": "cpi_general_services"})
c = a.merge(b, on="ym")
c["year"] = c.ym // 100; c["month"] = c.ym % 100
with gzip.open(RAW / "maikin_jissu_cumulative.csv.gz", "rb") as f:
    d = pd.read_csv(io.StringIO(f.read().decode("cp932")), dtype={"産業分類": str, "月": str, "規模": str})
d["産業分類"] = d["産業分類"].str.strip(); d["規模"] = d["規模"].astype(str).str.strip()
d = d[(d["種別"] == "実数") & (d["月"] != "CY") & (d["規模"] == "T")]
def hourly(ind, typ, key):
    x = d[(d["産業分類"] == ind) & (d["就業形態"] == typ)].copy()
    x["year"] = x["年"].astype(int); x["month"] = x["月"].astype(int)
    x[key] = x["所定内給与"] / x["所定内労働時間"]
    return x[["year", "month", key]].drop_duplicates(["year", "month"])
w = hourly("M76", 0, "wage_restaurant").merge(hourly("M", 2, "wage_M_part"), on=["year", "month"], how="outer") \
    .merge(hourly("TL", 2, "wage_TL_part"), on=["year", "month"], how="outer")
m = c.merge(w, on=["year", "month"], how="left").sort_values(["year", "month"]).reset_index(drop=True)
m = m[m.year >= 2005]
m.to_csv(DATA / "monthly.csv", index=False, float_format="%.4f")
print(m.tail(3).to_string()); print(m.isna().sum().to_dict())

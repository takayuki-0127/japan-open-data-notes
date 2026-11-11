"""02 整形：物価6系列と賃金（指数・公表の伸び率）を月次の1表にそろえる。"""
import pandas as pd
from common import RAW, DATA, CPI

c = pd.read_csv(RAW / "cpi.csv", header=None, dtype=str)
codes = c.iloc[2].tolist()
body = c[c[0].str.fullmatch(r"\d{6}", na=False)]
cpi = pd.DataFrame({"month": pd.to_datetime(body[0], format="%Y%m")})
for k in CPI:
    cpi[f"cpi_{k}"] = pd.to_numeric(body[codes.index(k)], errors="coerce").values

w = pd.read_csv(RAW / "wage.csv", dtype=str)
w = w[w["月"].str.fullmatch(r"\d\d") & (w["就業形態"].str.strip() == "0")]
cols = {"現金給与総額": "total", "きまって支給する給与": "regular",
        "実質賃金指数（現金給与総額）": "real_total", "実質賃金指数（きまって支給する給与）": "real_regular"}
out = []
for kind, pre in [("指数", "idx_"), ("伸び率、日数差、ポイント差", "pub_")]:
    x = w[w["種別"] == kind]
    d = pd.DataFrame({"month": pd.to_datetime(x["年"] + "-" + x["月"] + "-01")})
    for a, b in cols.items():
        d[pre + b] = pd.to_numeric(x[a], errors="coerce").values
    out.append(d.set_index("month"))
wage = out[0].join(out[1], how="outer").reset_index()
m = cpi.merge(wage, on="month", how="outer").sort_values("month").reset_index(drop=True)
m.to_csv(DATA / "monthly.csv", index=False)
print(m.dropna(subset=["pub_total"]).iloc[[0, -1]].T)

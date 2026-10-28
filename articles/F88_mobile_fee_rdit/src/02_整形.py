import pandas as pd
from common import RAW, DATA
d = pd.read_csv(RAW / "cpi_2020base_chubunrui.csv", header=None, dtype=str)
hdr = d.iloc[0].tolist(); wt = d.iloc[5].tolist()
cols = ["総合", "生鮮食品を除く総合", "生鮮食品及びエネルギーを除く総合", "通信", "情報通信関係費", "交通・通信"]
body = d.iloc[6:].copy(); body.columns = hdr
body = body[body["類・品目"].str.match(r"^\d{6}$", na=False)]
s = body.set_index("類・品目")[cols].apply(pd.to_numeric, errors="coerce")
s.index = pd.PeriodIndex([f"{x[:4]}-{x[4:]}" for x in s.index], freq="M")
s = s.loc["2000-01":]
s.to_csv(DATA / "cpi_monthly.csv")
w = pd.Series({c: int(wt[hdr.index(c)]) for c in cols}, name="weight_per_10000")
w.to_csv(DATA / "weights_2020base.csv")
print(s.tail(3)); print(w)

"""受診者数・対象者数（国保の被保険者、40〜69歳、大腸がん検診）と共変量の表を作る。"""
import io, csv, json
import numpy as np, pandas as pd
from common import RAW, DATA

raw = json.load(open(RAW / "f19_cancer_screening_raw.json"))
YEAR = {"R3": 2021, "R4": 2022, "R5": 2023, "R6": 2024}
rows = []
for k, t in raw.items():
    for r in csv.reader(io.StringIO(t)):
        if not r or not r[0].strip().isdigit():
            continue
        code = int(r[0])
        if code == 0 or code % 1000 == 0:      # 全国・都道府県の行
            continue
        def num(x):
            x = x.strip()
            if x == "-":
                return 0.0
            try:
                return float(x)
            except ValueError:
                return np.nan                     # 「…」= 計数不詳
        rows.append(dict(code=code, name=r[1].strip(), year=YEAR[k],
                         n_colon=num(r[12]), y_colon=num(r[14]),
                         n_lung=num(r[11]), y_lung=num(r[13])))
d = pd.DataFrame(rows)
d["pref"] = d.code // 1000
print("行数", d.groupby("year").size().to_dict())

s = pd.read_csv(RAW / "SSDSE-A-2026.csv", encoding="cp932", skiprows=[0, 1])
s["code"] = s["地域コード"].str[1:].astype(int)
x = pd.DataFrame({
    "code": s.code,
    "pop": s["総人口"],
    "aged": s["65歳以上人口"] / s["総人口"],
    "logdens": np.log(s["総人口"] / s["可住地面積"].replace(0, np.nan)),
    "clinic": s["一般診療所数"] / s["総人口"] * 1e4,
    "hosp": s["一般病院数"] / s["総人口"] * 1e4,
    "primary": s["第1次産業就業者数"] / s["就業者数"],
    "single": s["単独世帯数"] / s["一般世帯数"],
})
d = d.merge(x, on="code", how="left")
print("共変量なし", d[d["pop"].isna()].code.unique()[:10], d["pop"].isna().sum())
d.to_csv(DATA / "screening_long.csv", index=False)
print("ok")

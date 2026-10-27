"""data/raw の3表を、分析しやすい形（年×年齢など）に整える"""
import io
import numpy as np
import pandas as pd
from common import RAW, DATA, AGES


def read_raw(name):
    txt = (RAW / name).read_text(encoding="utf-8-sig")
    return pd.read_csv(io.StringIO(txt), header=None, dtype=str)


def num(s):
    return pd.to_numeric(s.astype(str).str.replace(",", "").str.strip(), errors="coerce")


# 1) 年齢各歳別出生率（年×年齢、1947年以降の毎年）
t = read_raw("ipss_T04-09_asfr_single_year.csv")
hdr = t.iloc[2, 1:].str.replace("年", "").str.strip()
rows = t[t[0].fillna("").str.strip().isin([str(a) for a in AGES])]
asfr = pd.DataFrame(rows.iloc[:, 1:].apply(num).values.T, columns=AGES.astype(int))
asfr.insert(0, "year", hdr.astype(int).values)
asfr = asfr[asfr.year >= 1950].reset_index(drop=True)
tot = num(t[t[0].fillna("").str.replace(" ", "").str.strip() == "合計"].iloc[0, 1:]).values
tot = pd.Series(tot, index=hdr.astype(int).values)
asfr["tfr_pub"] = asfr.year.map(tot)
asfr.to_csv(DATA / "asfr_single_year.csv", index=False)

# 2) 出生順位別の合計特殊出生率と平均出生年齢（1975年以降は毎年）
o = read_raw("ipss_T04-16_tfr_by_order.csv")
o = o[o[0].fillna("").str.strip().str.fullmatch(r"\d{4}")].copy()
cols = ["year", "tfr", "tfr1", "tfr2", "tfr3", "tfr4", "tfr5p", "mab", "mab1", "mab2", "mab3", "mab4", "mab5p"]
o = o.iloc[:, :13]
o.columns = cols
o = o.apply(num)
o["year"] = o.year.astype(int)
o.to_csv(DATA / "order_tfr_mab.csv", index=False)

# 3) コーホート（15歳になった年）ごとの累積出生率（年齢各歳）
c = read_raw("ipss_T04-11_cohort_cumulative.csv")
ch = c.iloc[2, 1:].str.replace("年", "").str.strip()
cr = c[c[0].fillna("").str.strip().isin([str(a) for a in AGES])]
cum = pd.DataFrame(cr.iloc[:, 1:].apply(num).values, index=AGES, columns=ch.astype(int).values)
cum.index.name = "age"
cum.to_csv(DATA / "cohort_cumulative.csv")

print("asfr", asfr.shape, asfr.year.min(), asfr.year.max())
print("order", o.shape, o.year.min(), o.year.max())
print("cohort", cum.shape, cum.columns.min(), cum.columns.max())

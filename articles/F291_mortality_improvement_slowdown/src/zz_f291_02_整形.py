"""02 整形：JMD の各歳の死亡数・曝露人口を5歳階級にまとめる（区分の m＝Σ死亡数÷Σ曝露）。"""
import pandas as pd
from common import RAW, DATA, GROUPS, GLABEL, group_of
d = pd.read_csv(RAW / "jmd_mx_long_from_F86.csv")
d["age"] = d["age"].astype(str).str.replace("+", "", regex=False).astype(int)
d["g"] = d["age"].map(group_of)
g = d.groupby(["sex", "year", "g"], as_index=False)[["deaths", "exposure"]].sum()
g["mx"] = g.deaths / g.exposure
g["label"] = g.g.map(lambda i: GLABEL[i])
g.to_csv(DATA / "group_mx.csv", index=False)
d[["sex", "year", "age", "deaths", "exposure", "mx"]].to_csv(DATA / "single_mx.csv", index=False)
print(g.year.min(), g.year.max(), len(g), d.age.max())

"""F177 の整形：3つの例の分析用の表を data/ に作る

- data/ex1_heat_trend.csv  : 30地点、group（U/R）、mu1（年最高気温の上がり方、℃／100年）
- data/ex2_east_west.csv   : 47都道府県 × F80 で選ばれた100指標、east（1=東日本17都道県）
- data/ex2_meta.csv        : 100指標の名前と単位
- data/ex3_lodging_gap.csv : 3つの災害（コロナ前）について、被災県と、対照になりうる各県の「季節をならした log 宿泊者数」
"""
import numpy as np
import pandas as pd
from common import RAW, DATA

# 例1：F168
g = pd.read_csv(RAW / "f168_gev_linear_1901_2025.csv")
g[["station", "group", "n", "first", "mu1", "se"]].to_csv(DATA / "ex1_heat_trend.csv", index=False)

# 例2：F80（F80 と同じ100指標、同じ東日本の定義）
X = pd.read_csv(RAW / "f80_indicators_2026.csv", index_col=0)
cols = pd.read_csv(RAW / "f80_chosen_100.csv").code.tolist()
EAST = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 19, 20]
E = X[cols].copy()
E.insert(0, "east", E.index.isin(EAST).astype(int))
E.to_csv(DATA / "ex2_east_west.csv")
meta = pd.read_csv(RAW / "f80_indicator_meta.csv", index_col=0).loc[cols]
meta.to_csv(DATA / "ex2_meta.csv")

# 例3：F98（事例の定義・季節のならし方は F98 と同じ）
EVENTS = {
    "E1": dict(name="熊本地震", start="2016-04", tr=["43熊本県", "44大分県"]),
    "E2": dict(name="平成30年7月豪雨", start="2018-07", tr=["33岡山県", "34広島県", "38愛媛県"]),
    "E3": dict(name="北海道胆振東部地震", start="2018-09", tr=["01北海道"]),
}
EXTRA = {"E5": dict(start="2017-07", tr=["40福岡県", "44大分県"])}
OTHER = [("2015-03", ["15新潟県", "16富山県", "17石川県", "20長野県"]),
         ("2016-03", ["01北海道", "02青森県"])]
PRE, H = 24, 16

d = pd.read_csv(RAW / "f98_panel.csv", parse_dates=["date"])
y = np.log(d.pivot(index="date", columns="pref", values="japanese"))
names = y.columns
code = {int(n[:2]): n for n in names}
p = pd.read_csv(RAW / "f98_pairs.csv")
A = {}
for r in p[p.adj == 1].itertuples():
    A.setdefault(code[r.o], set()).add(code[r.d])

rows = []
for eid, ev in EVENTS.items():
    t0 = pd.Timestamp(ev["start"])
    lo = t0 - pd.DateOffset(months=PRE)
    hi = min(t0 + pd.DateOffset(months=H), pd.Timestamp("2020-01-01"))
    out = set(ev["tr"])
    for q in ev["tr"]:
        out |= A.get(q, set())
    for e in list(EVENTS.values()) + list(EXTRA.values()):
        if lo <= pd.Timestamp(e["start"]) <= hi:
            out |= set(e["tr"])
    for s, ps in OTHER:
        if lo <= pd.Timestamp(s) <= hi:
            out |= set(ps)
    donors = [c for c in names if c not in out]
    pre = y[(y.index >= lo) & (y.index < t0)]
    m = pre.groupby(pre.index.month).mean()
    s = y - m.loc[y.index.month].values
    s = s[(s.index >= lo) & (s.index <= hi)]
    k = (s.index.year - t0.year) * 12 + s.index.month - t0.month
    for c in ev["tr"] + donors:
        for kk, v in zip(k, s[c].values):
            rows.append(dict(event=eid, name=ev["name"], pref=c, role="treated" if c in ev["tr"] else "donor", k=int(kk), s=v))
pd.DataFrame(rows).to_csv(DATA / "ex3_lodging_gap.csv", index=False)
print("ok")

"""03b 失われた延べ宿泊者数の目安：開始月から、−5%以内に戻る前の月まで（戻らなかった県は、見た期間のうち差がマイナスの月）
実績 ×（1/exp(差) − 1）を足す。「対照の県と同じ動きをしていたら」という仮定の上の数字"""
import numpy as np
import pandas as pd
from common import *
P = pd.read_csv(DATA / "panel.csv", parse_dates=["date"]).pivot(index="date", columns="pref", values="japanese")
eff = pd.read_csv(RES / "effects.csv"); rec = pd.read_csv(RES / "recovery.csv")
rows = []
for r in rec.itertuples():
    ev = EVENTS[r.event]; t0 = pd.Timestamp(ev["start"])
    prefs = ev["tr"] if "／" not in r.name else [p for p in ev["tr"] if p[2:] == r.tr]
    e = eff[eff.name == r.name].set_index("k").effect
    upto = int(r.thr5) - 1 if not pd.isna(r.thr5) else int(r.h)
    lost, base = 0.0, 0.0
    for k in range(0, upto + 1):
        d = t0 + pd.DateOffset(months=k); act = P.loc[d, prefs].sum()
        if e[k] < 0:
            lost += act * (np.exp(-e[k]) - 1)
    yr = P.loc[(P.index >= t0 - pd.DateOffset(months=12)) & (P.index < t0), prefs].sum().sum()
    rows.append(dict(name=r.name, months=upto + 1, lost=round(lost), year_before=int(yr), share_of_year=lost / yr))
d = pd.DataFrame(rows); d.to_csv(RES / "lost_nights.csv", index=False); print(d.to_string())

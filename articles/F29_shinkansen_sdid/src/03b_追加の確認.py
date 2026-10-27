"""03b 追加の確認：開業日を前にずらした時間のプラセボ（2013/3・2014/3）と、ASCM の罰則の強さ"""
import json
import numpy as np, pandas as pd
from common import *
W = load_panel("japanese")
donors = [p for p in W.columns if p not in TREATED + BASE_EXCL]
rows = []
for fake, pre0 in [("2013-03-01", "2011-03-01"), ("2014-03-01", "2012-01-01")]:
    f = pd.Timestamp(fake)
    y = prep(W, pre0=pd.Timestamp(pre0), post1=pd.Timestamp("2015-02-01"), open_=f)
    for tr in TREATED:
        r = dict(fake_open=fake[:7], pre_start=pre0[:7], pref=tr)
        r["SCM"] = np.expm1(scm(y, tr, donors, f)["att"]) * 100
        r["SDID"] = np.expm1(sdid(y, tr, donors, f)["att"]) * 100
        r["ASCM"] = np.expm1(ascm(y, tr, donors, f)["att"]) * 100
        r["DID"] = np.expm1(did(y, tr, donors, f)["att"]) * 100
        # 同じ偽の開業日で、対照県それぞれの SDID（分布の中での位置）
        pl = [sdid(y, p, [q for q in donors if q != p], f)["att"] for p in donors]
        r["SDID_placebo_sd"] = float(np.std(np.expm1(pl) * 100, ddof=1))
        rows.append(r)
tp = pd.DataFrame(rows); tp.to_csv(RES / "placebo_in_time.csv", index=False); print(tp.round(2).to_string())
y = prep(W)
ar = []
for a in [0.01, 0.1, 1, 10, 100, 1000]:
    for tr in TREATED:
        ar.append(dict(alpha=a, pref=tr, ASCM=np.expm1(ascm(y, tr, donors, alpha=a)["att"]) * 100))
ar = pd.DataFrame(ar); ar.to_csv(RES / "ascm_alpha.csv", index=False); print(ar.round(2).to_string())

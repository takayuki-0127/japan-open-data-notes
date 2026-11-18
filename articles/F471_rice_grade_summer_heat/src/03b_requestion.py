"""問い直し：2023年の下がり方は、同じ県の中でコシヒカリとそれ以外の品種で違ったか（2016〜2024年産の銘柄別の表）。"""
import json, pathlib
import numpy as np
import pandas as pd
from common import SMALL

ROOT = pathlib.Path(__file__).resolve().parent.parent
D = ROOT / "data"; R = ROOT / "results"
PREFS = [p for p in pd.read_csv(D / "panel.csv").pref.unique() if p != "全国"]
V = pd.read_csv(D / "varieties.csv")
V = V[~V.pref.isin(SMALL)]
base = V[(V.year >= 2016) & (V.year <= 2022)]
nb = base.groupby(["pref", "variety"]).agg(n_years=("year", "nunique"), base_r1=("r1", "mean"), base_total=("total", "mean")).reset_index()
v23 = V[V.year == 2023][["pref", "variety", "total", "r1"]].rename(columns={"total": "t23", "r1": "r23"})
x = nb.merge(v23, on=["pref", "variety"])
x = x[(x.n_years == 7) & (x.base_total >= 1000) & (x.t23 >= 1000)].copy()
x["drop"] = x.r23 - x.base_r1
x["koshi"] = x.variety.eq("コシヒカリ")
x = x.sort_values(["pref", "variety"], key=lambda s: s.map({p: i for i, p in enumerate(PREFS)}) if s.name == "pref" else s)
x.to_csv(R / "requestion_variety_pairs.csv", index=False, float_format="%.4f")
rows = []
for p, d in x.groupby("pref", sort=False):
    k = d[d.koshi]; o = d[~d.koshi]
    if len(k) and len(o):
        rows.append(dict(pref=p, koshi_drop=float(k["drop"].iloc[0]), other_drop=float(np.average(o["drop"], weights=o.t23)),
                         koshi_share23=float(k.t23.iloc[0] / d.t23.sum()), n_other=len(o)))
w = pd.DataFrame(rows)
w["gap"] = w.koshi_drop - w.other_drop
w.to_csv(R / "requestion_within_pref.csv", index=False, float_format="%.4f")
M = {"n_pairs": int(len(x)), "n_pref_both": int(len(w)),
     "n_pref_koshi_dropped_more": int((w.gap < 0).sum()),
     "median_gap": float(w.gap.median()),
     "weighted_drop_koshi": float(np.average(x[x.koshi]["drop"], weights=x[x.koshi].t23)),
     "weighted_drop_other": float(np.average(x[~x.koshi]["drop"], weights=x[~x.koshi].t23)),
     "share_koshi_national": {int(y): float(d[d.variety == "コシヒカリ"].total.sum() / d.total.sum()) for y, d in pd.read_csv(D / "varieties.csv").groupby("year")}}
ni = x[x.pref == "新潟"].set_index("variety")
M["niigata"] = {k: {"base_r1": float(ni.loc[k, "base_r1"]), "r23": float(ni.loc[k, "r23"]), "t23": float(ni.loc[k, "t23"])} for k in ni.index if k in ("コシヒカリ", "新之助", "こしいぶき")}
json.dump(M, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps(M, ensure_ascii=False, indent=1)); print(w.to_string())

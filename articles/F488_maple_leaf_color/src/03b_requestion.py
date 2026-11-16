"""問い直し（結果を見てから足した）：紅葉が早い地点（寒い地点）と遅い地点で、期間の短くなり方は違うか。
地点の平均の紅葉日で2つに分け（中央値で分ける）、期間の傾きを比べる。紅葉と落葉の傾きも並べる。"""
import json, pathlib
import numpy as np
import pandas as pd
from scipy import stats

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
out = {}
rows = []
for sp in ["kaede", "ichou"]:
    w = pd.read_csv(R / f"panel_{sp}.csv")
    recs = []
    for st, g in w.groupby("station", sort=True):
        if len(g) >= 20:
            recs.append({"station": st, "mean_color": g.color.mean(),
                         **{c: stats.theilslopes(g[c], g.year)[0] * 10 for c in ["color", "fall", "span"]}})
    s = pd.DataFrame(recs)
    cut = float(s.mean_color.median())
    s["group"] = np.where(s.mean_color <= cut, "早い地点", "遅い地点")
    gm = s.groupby("group")[["color", "fall", "span"]].median()
    rho = stats.spearmanr(s.mean_color, s.span)
    for gname, r in gm.iterrows():
        rows.append({"species": sp, "group": gname, "n": int((s.group == gname).sum()), "color_slope": round(float(r.color), 2),
                     "fall_slope": round(float(r.fall), 2), "span_slope": round(float(r.span), 2)})
    out[sp] = {"cut_doy": round(cut, 1), "spearman_meancolor_vs_spanslope": round(float(rho.statistic), 3), "p": round(float(rho.pvalue), 4),
               "groups": {g: {k: round(float(v), 2) for k, v in r.items()} for g, r in gm.iterrows()}}
pd.DataFrame(rows).to_csv(R / "requestion_groups.csv", index=False)
json.dump(out, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))

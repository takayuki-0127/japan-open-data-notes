"""問い直し：ばらつきが縮んだのは、低かった団体が上がったからか、高かった団体が下がったからか。
2008年と2025年の両方にある市区町村（同じ団体コード）で、2008年の水準と変化の関係を見る。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
d = pd.read_csv(ROOT / "data" / "laspeyres.csv", dtype={"code": str})
mu = d[d.kubun >= 3]
w = mu[mu.year == 2008][["code", "las"]].merge(mu[mu.year == 2025][["code", "kubun", "las"]], on="code", suffixes=("_08", "_25"))
w["chg"] = w.las_25 - w.las_08
w["q08"] = pd.qcut(w.las_08, 5, labels=["低い方の5分の1", "2", "3", "4", "高い方の5分の1"])
g = w.groupby("q08", observed=True).agg(n=("chg", "size"), las_08=("las_08", "median"), las_25=("las_25", "median"), chg_median=("chg", "median"),
                                         up_pct=("chg", lambda s: 100 * (s > 0).mean())).round(2)
g.to_csv(R / "requestion_quintiles.csv")
out = {"question": "ばらつきが縮んだのは、低い団体が上がったからか、高い団体が下がったからか",
       "n_matched": int(len(w)), "r_level_change": round(float(np.corrcoef(w.las_08, w.chg)[0, 1]), 3),
       "low_chg_median": float(g.chg_median.iloc[0]), "high_chg_median": float(g.chg_median.iloc[-1]),
       "low_up_pct": float(g.up_pct.iloc[0]), "high_up_pct": float(g.up_pct.iloc[-1]), "up_pct_all": round(float(100 * (w.chg > 0).mean()), 1)}
m = json.loads((R / "main.json").read_text(encoding="utf-8"))
m["requestion"] = out
(R / "main.json").write_text(json.dumps(m, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(g.to_string()); print(out)

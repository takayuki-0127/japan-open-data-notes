"""問い直し（結果を見てから足した）：人口が減った県で、建物の延面積そのものは減ったのか。
県ごとの延面積の変化率を人口の変化率で回帰し、人口が1%減ると延面積が何%動くかを見る。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
p = pd.read_csv(R / "pref_change_2011_2024.csv", index_col=0)
b, a = np.polyfit(p.pop_change_pct, p.area_change_pct, 1)
down = p[p.pop_change_pct < -10]
res = {"slope_area_on_pop": round(float(b), 3), "intercept": round(float(a), 2),
       "corr_area_pop": round(float(np.corrcoef(p.pop_change_pct, p.area_change_pct)[0, 1]), 3),
       "n_pref_pop_down_over10": int(len(down)), "mean_area_change_in_those": round(float(down.area_change_pct.mean()), 2),
       "mean_pop_change_in_those": round(float(down.pop_change_pct.mean()), 2),
       "n_pref_pop_up": int((p.pop_change_pct > 0).sum()), "mean_area_change_pop_up": round(float(p[p.pop_change_pct > 0].area_change_pct.mean()), 2)}
(R / "requestion.json").write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(res)

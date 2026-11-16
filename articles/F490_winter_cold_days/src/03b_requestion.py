"""問い直し（結果を見てから足した）：冬日の減り方（日数）は、もともとの冬日の多さでどう違うか。
冬日が年10日以上の地点（全区分）で、1961〜1990年の平均の冬日（横軸）と、1996〜2025年までの減った日数（縦軸）の関係を2次の式で当てはめ、
減り方が最も大きくなる「もともとの冬日の数」を求める。大都市と15地点の差が、この形でどこまで説明できるかも見る。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
T = pd.read_csv(R / "station_table.csv")
t = T[T.days_tmin_lt0_a >= 10].copy()
t["drop_days"] = t.days_tmin_lt0_b - t.days_tmin_lt0_a
c = np.polyfit(t.days_tmin_lt0_a, t.drop_days, 2)
peak_x = float(-c[1] / (2 * c[0])) if c[0] > 0 else np.nan
t["pred"] = np.polyval(c, t.days_tmin_lt0_a)
t["resid"] = t.drop_days - t.pred
g = t.groupby("group")[["drop_days", "pred", "resid"]].mean()
t[["station", "group", "days_tmin_lt0_a", "drop_days", "pred", "resid"]].round(2).to_csv(R / "requestion_baseline.csv", index=False)
out = {"coef": [round(float(x), 6) for x in c], "largest_drop_at_baseline_days": round(peak_x, 1),
       "largest_drop_pred_days": round(float(np.polyval(c, peak_x)), 1) if not np.isnan(peak_x) else None,
       "group_mean_drop": {k: round(float(v), 1) for k, v in g.drop_days.items()},
       "group_mean_pred": {k: round(float(v), 1) for k, v in g.pred.items()},
       "group_mean_resid": {k: round(float(v), 1) for k, v in g.resid.items()},
       "r2": round(float(1 - ((t.drop_days - t.pred) ** 2).sum() / ((t.drop_days - t.drop_days.mean()) ** 2).sum()), 3), "n": int(len(t))}
json.dump(out, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))

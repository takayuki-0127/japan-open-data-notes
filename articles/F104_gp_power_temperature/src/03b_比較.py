"""03b 比較：起点ごとのブートストラップで、モデル間の MAPE の差の95%区間を出す。季節別の当たり方も見る。"""
import importlib.util
import numpy as np
import pandas as pd
from common import RES

spec = importlib.util.spec_from_file_location("a", "03_分析.py")
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)
fc = pd.read_csv(RES / "fc_main.csv", parse_dates=["origin"])
fc["date"] = pd.to_datetime(fc.date.astype(str).str[:10])
D = "D_気温＋傾向＋季節"
pairs = [(D, "A_時刻だけ"), (D, "OLS_スプライン"), (D, "B_気温だけ"), ("C_気温＋傾向", D), ("E_D＋短期", D),
         (D + "｜気温シナリオ", "A_時刻だけ"), (D + "｜平年の気温", D + "｜気温シナリオ")]
rows = []
for k1, k2 in pairs:
    for lo, hi in [(0, 7), (7, 30), (30, 90), (0, 90)]:
        m, l, u = a.boot_diff(fc, k1, k2, lo, hi)
        rows.append(dict(比べるもの=f"{k1} − {k2}", horizon=f"{lo + 1}〜{hi}日先", 差=m, 下限=l, 上限=u))
out = pd.DataFrame(rows)
out.to_csv(RES / "diff_boot.csv", index=False)
print(out.to_string())
# 季節別（予測する日の月）
fc["ape"] = np.abs(np.exp(fc.m - fc.y) - 1) * 100
fc["cov"] = ((fc.y >= fc.lo) & (fc.y <= fc.hi)).astype(float)
fc["width"] = (np.exp(fc.hi) - np.exp(fc.lo)) / np.exp(fc.m) * 100
fc["季節"] = fc.date.dt.month.map({12: "冬", 1: "冬", 2: "冬", 3: "春", 4: "春", 5: "春", 6: "夏", 7: "夏", 8: "夏", 9: "秋", 10: "秋", 11: "秋"})
s = fc[fc.model.isin([D, "A_時刻だけ", "OLS_スプライン", D + "｜気温シナリオ"])].groupby(["model", "季節"])[["ape", "cov", "width"]].mean().round(2)
s.to_csv(RES / "score_by_season.csv")
print(s)

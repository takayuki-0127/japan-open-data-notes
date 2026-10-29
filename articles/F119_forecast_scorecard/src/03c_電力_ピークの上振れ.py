"""F92 の上振れの見込み（9月30日までで学習）が、記事のあとの2026年10月1〜28日にどれだけ収まったか

- 特徴量・モデル・較正は F92 の src（02_整形.py の build、03_分析.py の predict_fold）をそのまま使う。n_jobs だけ1にする
- 比べるもの：F92 のバックテストの10月（2020〜2025年）のカバー率
"""
import sys, importlib.util
import numpy as np, pandas as pd
from f119common import ART, ROOT, oct_daily

F92 = ART / "F92_power_quantile_forecast"
sys.path.insert(0, str(F92 / "src"))
def load(name, fn):
    s = importlib.util.spec_from_file_location(name, F92 / "src" / fn); m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m); return m
prep = load("f92p", "02_整形.py")
ana = load("f92a", "03_分析.py")
ana.P_PT["n_jobs"] = 1; ana.P_Q["n_jobs"] = 1
RES = ROOT / "results"

base = pd.read_csv(F92 / "data" / "raw" / "daily_tokyo.csv", parse_dates=["date"])
oc = oct_daily()
allraw = pd.concat([base, oc[[c for c in oc.columns]]], ignore_index=True)
tmp = ROOT / "data" / "_daily_tokyo_with_oct.csv"
allraw.to_csv(tmp, index=False)
prep.RAW = tmp.parent
d = prep.build(tmp.name)
tr, te = d[d.date < "2026-10-01"], d[(d.date >= "2026-10-01")]
p = ana.predict_fold(tr, te)
p.to_csv(RES / "power_oct2026_peak_pred.csv", index=False)

rows = []
def cover(g, label):
    for k, lab in ana.METHODS.items():
        for t in (0.9, 0.95, 0.99):
            rows.append({"期間": label, "方法": lab, "tau": t, "日数": len(g),
                         "カバー率(%)": 100 * (g.actual <= g[f"{k}_{t}"]).mean(),
                         "上乗せ(%)": 100 * ((g[f"{k}_{t}"] - g[f"{k}_0.5"]) / g[f"{k}_0.5"]).mean()})
    for m in (3, 5, 8):
        rows.append({"期間": label, "方法": f"点予測＋一律{m}%", "tau": np.nan, "日数": len(g),
                     "カバー率(%)": 100 * (g.actual <= g[f"fixed{m}"]).mean(), "上乗せ(%)": m})
    rows.append({"期間": label, "方法": "点予測のMAPE", "tau": np.nan, "日数": len(g),
                 "カバー率(%)": np.nan, "上乗せ(%)": 100 * ((g.point - g.actual).abs() / g.actual).mean()})
cover(p, "2026年10月1〜28日（記事のあと）")
h = pd.read_csv(F92 / "results" / "pred_tokyo.csv", parse_dates=["date"])
h10 = h[h.date.dt.month == 10]
cover(h10, "2020〜2025年の10月（F92 のバックテスト）")
cover(h, "F92 のバックテスト全体")
C = pd.DataFrame(rows)
C.to_csv(RES / "power_oct2026_peak_coverage.csv", index=False)
print(C[C.tau.isin([0.95, 0.99]) | C.方法.str.startswith("点")].round(2).to_string())
# 10月の年ごと（点予測＋残差の分位点 95%）
yy = h10.groupby(h10.date.dt.year).apply(lambda g: 100 * (g.actual <= g["conf_0.95"]).mean())
print(yy.round(1))
yy.rename("conf95_coverage").to_csv(RES / "power_oct_by_year_conf95.csv")

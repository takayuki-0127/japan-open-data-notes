"""問い直し（結果を見てから足した）：季節ごとに、日本と世界の上昇率と倍率はどう違うか（1898〜2025年）。
冬は前年12月〜2月で、日本の1898年の冬は前年12月を含む値。乱数は使わない。"""
import json, pathlib
import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
S = pd.read_csv(ROOT / "data" / "seasonal.csv")
S = S[S.year.between(1898, 2025)]
rows = []
for n, lab in [("winter", "冬（12〜2月）"), ("spring", "春（3〜5月）"), ("summer", "夏（6〜8月）"), ("autumn", "秋（9〜11月）")]:
    d = S.dropna(subset=[f"japan_{n}", f"world_{n}"])
    x = d.year.values.astype(float)
    bj = np.polyfit(x, d[f"japan_{n}"].values, 1)[0] * 100
    bw = np.polyfit(x, d[f"world_{n}"].values, 1)[0] * 100
    dd = d[f"japan_{n}"].values - d[f"world_{n}"].values
    m = sm.OLS(dd, sm.add_constant(x)).fit(cov_type="HAC", cov_kwds={"maxlags": 3})
    b, se = m.params[1] * 100, m.bse[1] * 100
    resid = d[f"japan_{n}"].values - np.polyval(np.polyfit(x, d[f"japan_{n}"].values, 1), x)
    rows.append({"season": n, "label": lab, "n": len(d), "y0": int(d.year.min()), "japan": round(bj, 3), "world": round(bw, 3),
                 "ratio": round(bj / bw, 3), "diff": round(b, 3), "lo90": round(b - 1.645 * se, 3), "hi90": round(b + 1.645 * se, 3),
                 "japan_resid_sd": round(float(np.std(resid, ddof=2)), 3)})
T = pd.DataFrame(rows); T.to_csv(R / "requestion_seasons.csv", index=False)
out = {r.season: {k: (v.item() if hasattr(v, "item") else v) for k, v in r.items() if k not in ("season",)} for _, r in T.iterrows()}
json.dump(out, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(T.to_string())

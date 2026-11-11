"""F271 02 整形：業態×月の販売額（億円）、前年同月比、直近12か月の前年比、「いつもの揺れ」の帯と判定。"""
import os, json
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
d = pd.read_csv(os.path.join(ROOT, "data", "raw", "sales_monthly_6types.csv"))
G = ["百貨店", "スーパー", "コンビニ", "ドラッグストア", "ホームセンター", "家電大型専門店"]
w = d.pivot(index="ym", columns="業態", values="販売額_百万円")[G].sort_index()
assert w.notna().all().all() and len(w) == 152
w["6業態合計"] = w[G].sum(axis=1)
lv = w / 100.0  # 億円
months = list(lv.index)
idx = {m: i for i, m in enumerate(months)}
EXCL = {m for m in months if "2020-03" <= m <= "2021-12"}
rows = []
cols = G + ["6業態合計"]
for g in cols:
    s = lv[g].values
    for i, m in enumerate(months):
        r = dict(ym=m, g=g, lvl=s[i])
        r["yoy"] = (s[i] / s[i - 12] - 1) * 100 if i >= 12 else np.nan
        r["yoy12"] = (s[i - 11:i + 1].sum() / s[i - 23:i - 11].sum() - 1) * 100 if i >= 23 else np.nan
        rows.append(r)
p = pd.DataFrame(rows)
# いつもの揺れ：その月の前36か月（2020-03〜2021-12 を除く）の前年同月比の平均±1.645×標準偏差
band_lo, band_hi, band_n = [], [], []
yo = p.pivot(index="ym", columns="g", values="yoy")
for _, r in p.iterrows():
    i = idx[r.ym]
    win = [months[j] for j in range(i - 36, i) if j >= 12 and months[j] not in EXCL]
    v = yo.loc[win, r.g].dropna().values if win else np.array([])
    if len(v) >= 12:
        mu, sd = v.mean(), v.std(ddof=1)
        band_lo.append(mu - 1.645 * sd); band_hi.append(mu + 1.645 * sd); band_n.append(len(v))
    else:
        band_lo.append(np.nan); band_hi.append(np.nan); band_n.append(len(v))
p["band_lo"], p["band_hi"], p["band_n"] = band_lo, band_hi, band_n
fl = ((p.yoy < p.band_lo) | (p.yoy > p.band_hi)).astype(float)
fl[p.band_lo.isna()] = np.nan
p["flag"] = fl
os.makedirs(os.path.join(ROOT, "data", "processed"), exist_ok=True)
p.to_csv(os.path.join(ROOT, "data", "processed", "panel.csv"), index=False, float_format="%.6f")
print(p.shape, p.ym.min(), p.ym.max(), "band n min (2017+)", p[p.ym >= "2017-01"].band_n.min())

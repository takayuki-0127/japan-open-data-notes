"""F261 整形：四半期のパネル（data/processed/panel_q.csv）と、公表回ごとの水準（vintage_levels.csv）を作る。"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW, OUT = ROOT / "data" / "raw", ROOT / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)

gdp = pd.read_csv(RAW / "real_gdp_sa_2026Q2_2nd.csv")
cao = pd.read_csv(RAW / "cao_gap_2026Q2_2nd.csv")
boj = pd.read_csv(RAW / "boj_gap_2026Oct.csv")
bojpg = pd.read_csv(RAW / "boj_potential_growth_2026Oct.csv")

p = gdp.rename(columns={"real_gdp_bn_yen_2020chain": "gdp"})
p["lny"] = np.log(p["gdp"])
p = p.merge(cao.rename(columns={"gap": "cao_gap", "pot_growth": "cao_pg"}), on="quarter", how="left")
p = p.merge(boj[["quarter", "output_gap"]].rename(columns={"output_gap": "boj_gap"}), on="quarter", how="left")

# 日銀の潜在成長率（年度半期、前年比）を四半期に割り当てる：FY t の H1 = t年Q2・Q3、H2 = t年Q4・t+1年Q1
rows = []
for _, r in bojpg.iterrows():
    fy, h = int(r.fy_half[2:6]), int(r.fy_half[-1])
    qs = [f"{fy}Q2", f"{fy}Q3"] if h == 1 else [f"{fy}Q4", f"{fy+1}Q1"]
    for q in qs:
        rows.append({"quarter": q, "boj_pg": r.pot_growth, "boj_c_tfp": r.c_tfp, "boj_c_capital": r.c_capital,
                     "boj_c_hours": r.c_hours, "boj_c_employed": r.c_employed})
p = p.merge(pd.DataFrame(rows), on="quarter", how="left")
y = p["quarter"].str[:4].astype(int)
q = p["quarter"].str[-1].astype(int)
p["fy"] = np.where(q == 1, y - 1, y)
p.to_csv(OUT / "panel_q.csv", index=False)
print("panel_q", p.shape, p.quarter.iloc[0], p.quarter.iloc[-1])

# 公表回ごとの水準：1994Q1 を 100 とし、1994Q2 以降の前期比（％、小数1桁）を積み上げる
v = pd.read_csv(RAW / "f50_vintages_real_sa_qoq.csv", index_col=0)
rel = pd.read_csv(RAW / "f50_releases.csv")
cols = [c for c in v.columns if c >= "1994Q2"]
recs = []
for _, r in rel.iterrows():
    g = v.loc[r.rid, cols]
    g = g.loc[: r.ref]
    if g.isna().any():
        raise SystemExit(f"missing growth in {r.rid}: {g[g.isna()].index.tolist()[:3]}")
    lvl = 100 * np.exp(np.cumsum(np.log1p(g.values / 100)))
    lv = np.concatenate([[100.0], lvl])
    recs.append(pd.DataFrame({"rid": r.rid, "ref": r.ref, "stage": r.stage,
                              "quarter": ["1994Q1"] + list(g.index), "level": lv}))
vl = pd.concat(recs)
vl.to_csv(OUT / "vintage_levels.csv.gz", index=False, float_format="%.6f", compression={"method": "gzip", "mtime": 0})
print("vintage_levels", vl.shape, vl.rid.nunique())

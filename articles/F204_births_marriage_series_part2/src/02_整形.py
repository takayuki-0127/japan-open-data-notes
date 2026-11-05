"""都道府県×年のパネルを作る（data/panel.csv）。"""
import numpy as np, pandas as pd
from common import RAW, DATA

b = pd.read_csv(RAW / "f204_births_order_pref.csv")
b = b[b.pref > 0]
w = pd.read_csv(RAW / "f160_women15_49_pref.csv")
# 15〜49歳の女性：国勢調査の4時点を対数で直線補間（2026年以降は使わない）
rows = []
for p, g in w.groupby("pref"):
    g = g.sort_values("year")
    for y in range(1995, 2026):
        if y < 2010:  # 2010年より前は 2010→2015 の変化率で延ばす
            r = np.log(g.w15_49.iloc[1] / g.w15_49.iloc[0]) / 5
            v = g.w15_49.iloc[0] * np.exp(r * (y - 2010))
        else:
            v = np.exp(np.interp(y, g.year, np.log(g.w15_49)))
        rows.append((y, p, v))
W = pd.DataFrame(rows, columns=["year", "pref", "w15_49"])
s = pd.read_csv(RAW / "ssdse_b_pref.csv")
c = pd.read_csv(RAW / "f118_pref_panel.csv", dtype={"pc": str})
c["pref"] = c.pc.astype(int)
P = b.merge(W, on=["year", "pref"], how="left").merge(s[["year", "pref", "marriages", "women15_64"]], on=["year", "pref"], how="left")
P = P.merge(c[["year", "pref", "D", "D_cap"]], on=["year", "pref"], how="left")
for k in ["total", "o1", "o2", "o3p", "marriages"]:
    P[f"r_{k}"] = P[k] / P.w15_49 * 1000   # 15〜49歳女性1,000人あたり
P["src"] = np.where(P.year <= 2016, "確定数", "概数（月報）")
P.to_csv(DATA / "panel.csv", index=False)
print(P.groupby("year")[["r_total", "r_o1", "r_o2", "r_o3p", "r_marriages"]].mean().round(2))

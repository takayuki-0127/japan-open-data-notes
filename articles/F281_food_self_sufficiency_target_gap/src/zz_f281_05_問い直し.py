"""F281 05 問い直し（結果を見てから足した）：
今の計画（令和2年・令和7年）の 45% は、これまでの国産熱量・総供給熱量の動き方で届く高さか。

- 国産熱量 N（1人1日）の5年ごとの変化率を 1965〜2025年度で並べ、2025年度 → 2030年度に要る変化率と比べる。
- N は「自給率（整数％）× 総供給熱量」で近似（2024・2025年度は公表値）。総供給熱量は2019年度から推計方法が変わっている。
出力：results/F_reask.json、results/F_n_changes.csv
"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
P, RES = ROOT / "data" / "processed", ROOT / "results"
ssr = pd.read_csv(P / "ssr_series.csv")
s = pd.read_csv(P / "series_long.csv")
plans = pd.read_csv(ROOT / "data" / "plans.csv").set_index("plan")

r = ssr[ssr.indicator == "供給熱量ベースの総合食料自給率"].set_index("fy").value
S = s[(s.item == "合計") & (s["var"] == "kcal")].set_index("fy").value
df = pd.DataFrame({"ssr": r, "S": S}).dropna()
df["N"] = df.ssr / 100 * df.S
df.loc[2024, "N"], df.loc[2025, "N"] = 858.0, 830.0
df.loc[2025, "S"] = 2237.4
df["N_chg5"] = (df.N / df.N.shift(5) - 1) * 100
df["S_chg5"] = (df.S / df.S.shift(5) - 1) * 100
df.to_csv(RES / "F_n_changes.csv")

N25, S25 = 830.0, 2237.4
need = {}
for pl in ["R2", "R7"]:
    Nt, St = plans.loc[pl, "N_target"], plans.loc[pl, "S_target"]
    need[pl] = {"N_target": Nt, "S_target": St, "N_change_needed_pct": (Nt / N25 - 1) * 100, "S_change_planned_pct": (St / S25 - 1) * 100,
                "per_year_N_pct": ((Nt / N25) ** (1 / 5) - 1) * 100}
    # N が今のままなら、S をどこまで下げれば 45% か
    need[pl]["S_needed_if_N_flat"] = N25 / 0.45
    need[pl]["S_change_if_N_flat_pct"] = (N25 / 0.45 / S25 - 1) * 100

c = df.N_chg5.dropna()
c90 = df.loc[1990:, "N_chg5"].dropna()
out = {"N_chg5_all": {"n": int(len(c)), "max": float(c.max()), "argmax_fy": int(c.idxmax()), "median": float(c.median()),
                      "share_positive": float((c > 0).mean())},
       "N_chg5_since1990": {"n": int(len(c90)), "max": float(c90.max()), "argmax_fy": int(c90.idxmax()), "median": float(c90.median()),
                            "share_positive": float((c90 > 0).mean())},
       "S_chg5_min_all": float(df.S_chg5.min()), "S_chg5_min_fy": int(df.S_chg5.idxmin()),
       "need": need,
       "n_windows_reaching_R7": int((c >= need["R7"]["N_change_needed_pct"]).sum()),
       "n_windows_reaching_R2": int((c >= need["R2"]["N_change_needed_pct"]).sum()),
       "note": "N は自給率（整数）×総供給熱量の近似。2019年度から総供給熱量の推計方法が変わった（訪日客などの分を除く）。"}
(RES / "F_reask.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
print(json.dumps(out, ensure_ascii=False, indent=1))

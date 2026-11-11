"""05 問い直し（結果を見た後で足した）：
地方部の外国人延べ宿泊者数の目標（明日の日本を支える観光ビジョン：2030年に1億3,000万人泊）に、
全体の伸びと地方部の割合のどちらが効くか。2025年の確定値から延ばす単純な計算（予測ではない）。"""
import json, pathlib
import numpy as np
import pandas as pd
R = pathlib.Path(__file__).resolve().parents[1]
M = pd.read_csv(R / "results/A_metrics_by_year.csv")
f = M[M.who == "foreign"].set_index("year")
T25, L25, s25 = f.loc[2025, "total"], f.loc[2025, "local"], f.loc[2025, "local_share"]
TARGET = 1.3e8
need_cagr_local = (TARGET / L25) ** (1 / 5) - 1
cagr = {
    "2015→2019年の全体の伸び": (f.loc[2019, "total"] / f.loc[2015, "total"]) ** (1 / 4) - 1,
    "2024→2025年の全体の伸び": f.loc[2025, "total"] / f.loc[2024, "total"] - 1,
    "全体が年5%": 0.05,
}
shares = {"2025年の割合": s25, "2017年の山の割合": f.loc[2017, "local_share"], "2015〜19年の平均": f.loc[2015:2019, "local_share"].mean()}
rows = []
for cn, g in cagr.items():
    T30 = T25 * (1 + g) ** 5
    for sn, s in shares.items():
        rows.append({"全体の伸び": cn, "年率": g, "2030年の全体（万人泊）": T30 / 1e4, "地方部の割合": sn, "割合": s,
                     "2030年の地方部（万人泊）": T30 * s / 1e4, "目標に届くか": bool(T30 * s >= TARGET)})
    rows.append({"全体の伸び": cn, "年率": g, "2030年の全体（万人泊）": T30 / 1e4, "地方部の割合": "目標に要る割合", "割合": TARGET / T30,
                 "2030年の地方部（万人泊）": TARGET / 1e4, "目標に届くか": None})
D = pd.DataFrame(rows)
D.to_csv(R / "results/D_reask_target.csv", index=False)
past = {f"{y0}→{y1}": (f.loc[y1, "local"] / f.loc[y0, "local"]) ** (1 / (y1 - y0)) - 1 for y0, y1 in [(2011, 2019), (2015, 2019), (2023, 2025), (2024, 2025)]}
out = {"local_2025": L25, "need_cagr_local_2025_2030": need_cagr_local, "past_local_cagr": past, "table": rows}
(R / "results/reask.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float))
print("need", round(need_cagr_local, 4), {k: round(v, 4) for k, v in past.items()})
print(D.round(3).to_string())

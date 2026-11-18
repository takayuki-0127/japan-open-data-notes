"""形別・年齢別の推移、49歳以下の割合と形の構成、49歳以下の変化の内訳、仮説の判定、頑健性。乱数は使わない。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES = ROOT / "results"
N = pd.read_csv(ROOT / "data" / "new_farmers.csv")
END = int(N.year.max())
P = {c: N.pivot(index="year", columns="form", values=c) for c in ["all", "le39", "le49", "a40_49", "a50", "a60", "a65"]}
FL = {"jiei": "新規自営農業就農者", "koyo": "新規雇用就農者", "sannyu": "新規参入者", "total": "計"}

ser = pd.DataFrame(index=P["all"].index)
for f in ["total", "jiei", "koyo", "sannyu"]:
    ser[f"all_{f}"] = P["all"][f]; ser[f"le49_{f}"] = P["le49"][f]; ser[f"le39_{f}"] = P["le39"][f]
ser["le49_share"] = 100 * ser.le49_total / ser.all_total
ser["le39_share"] = 100 * ser.le39_total / ser.all_total
for f in ["jiei", "koyo", "sannyu"]:
    ser[f"form_share_all_{f}"] = 100 * ser[f"all_{f}"] / ser.all_total
    ser[f"form_share_le49_{f}"] = 100 * ser[f"le49_{f}"] / ser.le49_total
ser["jiei_60plus_share"] = 100 * (P["a60"]["jiei"] + P["a65"]["jiei"]) / P["all"]["jiei"]
ser["jiei_65plus_share"] = 100 * P["a65"]["jiei"] / P["all"]["jiei"]
ser["total_65plus_share"] = 100 * P["a65"]["total"] / P["all"]["total"]
ser.round(3).to_csv(RES / "national_series.csv")

# 年齢の構成（計）
ages = pd.DataFrame({"15〜39歳": P["le39"]["total"], "40〜49歳": P["a40_49"]["total"], "50〜59歳": P["a50"]["total"],
                     "60〜64歳": P["a60"]["total"], "65歳以上": P["a65"]["total"]})
ages.to_csv(RES / "age_total.csv")

# 49歳以下の変化の内訳（形ごとの人数の差）
def split(a, b, row="le49"):
    t = P[row]
    return {"from": a, "to": b, "total_from": float(t.loc[a, "total"]), "total_to": float(t.loc[b, "total"]),
            "change": float(t.loc[b, "total"] - t.loc[a, "total"]),
            **{f: float(t.loc[b, f] - t.loc[a, f]) for f in ["jiei", "koyo", "sannyu"]}}
y49_peak = int(P["le49"]["total"].idxmax())
splits = [split(2007, END), split(2010, END), split(y49_peak, END)]
pd.DataFrame(splits).to_csv(RES / "le49_change_by_form.csv", index=False)

# 仮説
h1 = float(ser.loc[END, "all_total"] / ser.loc[2007, "all_total"] - 1)
h2 = (float(ser.loc[2007, "le49_share"]), float(ser.loc[END, "le49_share"]))
h3 = (float(ser.loc[2010, "form_share_le49_koyo"]), float(ser.loc[END, "form_share_le49_koyo"]))
h4 = float(ser.loc[END, "jiei_60plus_share"])
hyp = {"H1": {"change": h1, "verdict": "支持" if h1 <= -0.3 else "外れ"},
       "H2": {"from": h2[0], "to": h2[1], "verdict": "支持" if h2[1] > h2[0] else "外れ"},
       "H3": {"from": h3[0], "to": h3[1], "diff": h3[1] - h3[0], "verdict": "支持" if h3[1] - h3[0] >= 10 else "外れ"},
       "H4": {"share": h4, "verdict": "支持" if h4 >= 50 else "外れ"}}

# 頑健性
def avg(s, y, k=1):
    return float(s.loc[y - k:y + k].mean()) if y + k <= END else float(s.loc[y - 2 * k:y].mean())
rob = []
rob.append({"check": "本計算", "total_change": h1, "le49_share_from": h2[0], "le49_share_to": h2[1], "koyo_in_le49_from": h3[0], "koyo_in_le49_to": h3[1]})
# 新規参入者を除く（自営＋雇用）
nos = lambda c: ser[f"{c}_jiei"] + ser[f"{c}_koyo"]
rob.append({"check": "新規参入者を除く（自営＋雇用）", "total_change": float(nos("all")[END] / nos("all")[2007] - 1),
            "le49_share_from": float(100 * nos("le49")[2007] / nos("all")[2007]), "le49_share_to": float(100 * nos("le49")[END] / nos("all")[END]),
            "koyo_in_le49_from": float(100 * ser.loc[2010, "le49_koyo"] / nos("le49")[2010]), "koyo_in_le49_to": float(100 * ser.loc[END, "le49_koyo"] / nos("le49")[END])})
# 39歳以下で見る（2006年から）
rob.append({"check": "39歳以下で見る（起点2006年）", "total_change": float(ser.loc[END, "all_total"] / ser.loc[2006, "all_total"] - 1),
            "le49_share_from": float(ser.loc[2006, "le39_share"]), "le49_share_to": float(ser.loc[END, "le39_share"]),
            "koyo_in_le49_from": float(100 * ser.loc[2006, "le39_koyo"] / ser.loc[2006, "le39_total"]), "koyo_in_le49_to": float(100 * ser.loc[END, "le39_koyo"] / ser.loc[END, "le39_total"])})
# 3年平均（2007〜2009年、2010〜2012年、2023〜2025年）
m3 = lambda s, a, b: float(s.loc[a:b].mean())
rob.append({"check": "3年平均（2007〜09年→2023〜25年。雇用の割合は2010〜12年→2023〜25年）", "total_change": m3(ser.all_total, 2023, 2025) / m3(ser.all_total, 2007, 2009) - 1,
            "le49_share_from": 100 * m3(ser.le49_total, 2007, 2009) / m3(ser.all_total, 2007, 2009), "le49_share_to": 100 * m3(ser.le49_total, 2023, 2025) / m3(ser.all_total, 2023, 2025),
            "koyo_in_le49_from": 100 * m3(ser.le49_koyo, 2010, 2012) / m3(ser.le49_total, 2010, 2012), "koyo_in_le49_to": 100 * m3(ser.le49_koyo, 2023, 2025) / m3(ser.le49_total, 2023, 2025)})
# 起点を2015年（49歳以下が最も多い年）にする
rob.append({"check": f"起点{y49_peak}年（49歳以下が最も多い年）", "total_change": float(ser.loc[END, "all_total"] / ser.loc[y49_peak, "all_total"] - 1),
            "le49_share_from": float(ser.loc[y49_peak, "le49_share"]), "le49_share_to": float(ser.loc[END, "le49_share"]),
            "koyo_in_le49_from": float(ser.loc[y49_peak, "form_share_le49_koyo"]), "koyo_in_le49_to": float(ser.loc[END, "form_share_le49_koyo"])})
robdf = pd.DataFrame(rob).round(4); robdf.to_csv(RES / "robustness.csv", index=False)

out = {"end": END, "y49_peak": y49_peak,
       "years": {str(y): {k: (None if pd.isna(ser.loc[y, k]) else float(ser.loc[y, k])) for k in ser.columns} for y in [2006, 2007, 2010, 2014, y49_peak, 2019, 2021, END]},
       "all_peak_since2007": {"year": int(ser.all_total.loc[2007:].idxmax()), "value": float(ser.all_total.loc[2007:].max())},
       "koyo_all_max": {"year": int(ser.all_koyo.idxmax()), "value": float(ser.all_koyo.max())},
       "splits": splits, "hypotheses": hyp, "robustness": robdf.to_dict("records")}
json.dump(out, open(RES / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
pd.set_option("display.width", 250)
print(ser[["all_total", "all_jiei", "all_koyo", "all_sannyu", "le49_total", "le49_share", "form_share_all_koyo", "form_share_le49_koyo", "form_share_le49_jiei", "form_share_le49_sannyu", "jiei_60plus_share", "total_65plus_share"]].round(1).to_string())
print(pd.DataFrame(splits)); print(robdf.to_string()); print({h: v["verdict"] for h, v in hyp.items()}, hyp)

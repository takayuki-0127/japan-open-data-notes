"""問い直し（結果を見てから足した）：リピーターの割合が上がった東アジアでは、10回以上来ている「常連」も増えたのか。地域のまとまりごとに見る。"""
import json, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
R = ROOT / "results"
sh = pd.read_csv(R / "repeat_by_nation_year.csv")
H = sh.pivot(index="nation", columns="year", values="heavy10"); F1 = sh.pivot(index="nation", columns="year", values="1回目")
G = {"東アジア": ["韓国", "台湾", "香港", "中国"], "東南アジア・インド": ["タイ", "シンガポール", "マレーシア", "インドネシア", "フィリピン", "ベトナム", "インド"],
     "欧米豪": ["英国", "ドイツ", "フランス", "米国", "カナダ", "オーストラリア"]}
rows = []
for k, cs in G.items():
    for y in H.columns:
        rows.append(dict(group=k, year=int(y), heavy10=float(H.loc[cs, y].mean()), first=float(F1.loc[cs, y].mean())))
t = pd.DataFrame(rows); t.to_csv(R / "requestion_groups.csv", index=False, float_format="%.3f")
out = {k: {"heavy10_2014": round(float(H.loc[cs, 2014].mean()), 1), "heavy10_2025": round(float(H.loc[cs, 2025].mean()), 1),
           "first_2014": round(float(F1.loc[cs, 2014].mean()), 1), "first_2025": round(float(F1.loc[cs, 2025].mean()), 1)} for k, cs in G.items()}
out["korea_heavy10"] = {int(y): round(float(H.loc["韓国", y]), 1) for y in [2014, 2019, 2025]}
out["taiwan_heavy10"] = {int(y): round(float(H.loc["台湾", y]), 1) for y in [2014, 2019, 2025]}
out["hongkong_heavy10"] = {int(y): round(float(H.loc["香港", y]), 1) for y in [2014, 2019, 2025]}
json.dump(out, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps(out, ensure_ascii=False, indent=1))

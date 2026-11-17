"""問い直し（結果を見てから足した）：休日の少ない産業で平均が増えたのは、「年間100日未満」の働き手が減ったからか、
「120日以上」が増えたからか。2009年に平均が少なかった3産業と多かった3産業で、階級の割合を比べる。"""
import json, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
d = pd.read_csv(ROOT / "data" / "holidays.csv")
m = json.load(open(R / "main.json", encoding="utf-8"))
low3, high3 = m["hypotheses"]["H3"]["low3"], m["hypotheses"]["H3"]["high3"]
Y0, Y1 = m["years"]
x = d[(d.kind == "industry") & (d.year.isin([Y0, Y1])) & (d.code.isin(low3 + high3))]
t = x.pivot(index="code", columns="year", values=["mean_days", "share_under100", "share_120plus"])
t.columns = [f"{a}_{b}" for a, b in t.columns]
t = t.loc[low3 + high3].round(2)
t.insert(0, "group", ["少ない3産業"] * 3 + ["多い3産業"] * 3)
t.to_csv(R / "requestion_classes.csv")
res = {c: {"under100": [float(t.loc[c, f"share_under100_{Y0}"]), float(t.loc[c, f"share_under100_{Y1}"])],
           "plus120": [float(t.loc[c, f"share_120plus_{Y0}"]), float(t.loc[c, f"share_120plus_{Y1}"])]} for c in low3 + high3}
res["low3_under100_change_mean"] = round(float((t.loc[low3, f"share_under100_{Y1}"] - t.loc[low3, f"share_under100_{Y0}"]).mean()), 1)
res["low3_120plus_change_mean"] = round(float((t.loc[low3, f"share_120plus_{Y1}"] - t.loc[low3, f"share_120plus_{Y0}"]).mean()), 1)
(R / "requestion.json").write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(t)
print(res["low3_under100_change_mean"], res["low3_120plus_change_mean"])

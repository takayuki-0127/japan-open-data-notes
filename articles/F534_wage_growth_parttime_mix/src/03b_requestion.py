"""問い直し（結果を見てから足した）：構成による押し下げは、事業所の規模でどう違うのか。"""
import json, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
d = pd.read_csv(ROOT / "data" / "maikin_tl_cy.csv", dtype={"size_code": str, "form_code": str})
SIZES = [("4", "500人以上"), ("5", "100〜499人"), ("7", "30〜99人"), ("9", "5〜29人")]
rows = []
for code, name in SIZES:
    x = d[d.size_code == code]
    w = x.pivot(index="year", columns="form_code", values="cash")
    t = x[x.form_code == "0"].set_index("year")
    p = t.part_workers / t.workers
    pb = p[1993]
    fx = lambda y: (1 - pb) * w.loc[y, "1"] + pb * w.loc[y, "2"]
    fixed = 100 * (fx(2025) / fx(1993) - 1); pub = 100 * (w.loc[2025, "0"] / w.loc[1993, "0"] - 1)
    rows.append({"size": name, "p_1993": p[1993], "p_2025": p[2025], "W_1993": w.loc[1993, "0"], "W_2025": w.loc[2025, "0"],
                 "growth_general": 100 * (w.loc[2025, "1"] / w.loc[1993, "1"] - 1),
                 "growth_part": 100 * (w.loc[2025, "2"] / w.loc[1993, "2"] - 1),
                 "growth_published": pub, "growth_fixed1993": fixed, "drag_pt": fixed - pub})
out = pd.DataFrame(rows)
out.to_csv(R / "requestion_by_size.csv", index=False, float_format="%.4f", lineterminator="\n")
m = json.load(open(R / "main.json", encoding="utf-8"))
m["requestion_by_size"] = out.set_index("size").round(4).to_dict(orient="index")
json.dump(m, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
print(out.round(3).to_string())

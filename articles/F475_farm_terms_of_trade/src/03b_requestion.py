"""問い直し（結果を見てから足した）：2008年前後の値上がりのときと比べて、戻り方は同じか。
基準の年（2007年・2020年）を100にして、0〜5年後の交易条件・農産物・資材・肥料・飼料を並べる。"""
import json, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
A = pd.read_csv(R / "annual_tot.csv").set_index("year")
rows = []
for name, b in [("2008年前後（基準2007年）", 2007), ("2021年以降（基準2020年）", 2020)]:
    for k in range(0, 6):
        y = b + k
        r = {"episode": name, "base": b, "k": k, "year": y}
        for c, lab in [("tot", "tot"), ("products", "products"), ("inputs", "inputs"), ("in_肥料", "fert"), ("in_飼料", "feed"),
                       ("products_ex_rice", "products_ex_rice")]:
            r[lab] = A.loc[y, c] / A.loc[b, c] * 100
        rows.append(r)
E_ = pd.DataFrame(rows)
E_.round(2).to_csv(R / "requestion_episodes.csv", index=False)
out = {}
for name, g in E_.groupby("episode", sort=False):
    g = g.set_index("k")
    t = g.loc[1:, "tot"]
    kmin = int(t.idxmin())
    back = [int(k) for k in g.index if k > kmin and g.loc[k, "tot"] >= 100]
    out[name] = {"trough_k": kmin, "trough_year": int(g.loc[kmin, "year"]), "trough_tot": round(float(t.min()), 2),
                 "first_back_k": back[0] if back else None,
                 "inputs_peak": round(float(g.loc[1:, "inputs"].max()), 2), "inputs_k5": round(float(g.loc[5, "inputs"]), 2),
                 "products_k5": round(float(g.loc[5, "products"]), 2), "tot_k5": round(float(g.loc[5, "tot"]), 2),
                 "products_ex_rice_k5": round(float(g.loc[5, "products_ex_rice"]), 2),
                 "fert_peak": round(float(g.loc[1:, "fert"].max()), 2), "feed_peak": round(float(g.loc[1:, "feed"].max()), 2),
                 "fert_k5": round(float(g.loc[5, "fert"]), 2), "feed_k5": round(float(g.loc[5, "feed"]), 2)}
json.dump(out, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(E_.round(1).to_string()); print(json.dumps(out, ensure_ascii=False, indent=1))

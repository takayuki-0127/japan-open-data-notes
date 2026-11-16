"""問い直し（結果を見てから足した）：1台あたりの走行キロは、コロナ前（2017〜19年度）に戻ったのか。車種ごとにも見る。"""
import json, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
R = ROOT / "results"
t = pd.read_csv(R / "private_car_gasoline_by_fy.csv", index_col="fy")
P, Q, C = [2017, 2018, 2019], [2023, 2024, 2025], [2020, 2021]
m = lambda c, ys: float(t.loc[ys, c].mean())
out = {"all": {"pre": round(m("km_per_car", P)), "covid": round(m("km_per_car", C)), "post": round(m("km_per_car", Q)),
               "post_vs_pre_pct": round((m("km_per_car", Q) / m("km_per_car", P) - 1) * 100, 1),
               "covid_vs_pre_pct": round((m("km_per_car", C) / m("km_per_car", P) - 1) * 100, 1)}}
rows = []
for k in ["regular", "small", "hybrid", "kei"]:
    c = f"kmcar_{k}"
    r = dict(kind=k, pre=m(c, P), covid=m(c, C), post=m(c, Q))
    r["post_vs_pre_pct"] = (r["post"] / r["pre"] - 1) * 100
    rows.append(r)
    out[k] = {kk: round(v, 1) for kk, v in r.items() if kk != "kind"}
pd.DataFrame(rows).to_csv(R / "requestion_km_per_car_by_kind.csv", index=False, float_format="%.3f")
json.dump(out, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps(out, ensure_ascii=False, indent=1))

"""問い直し（結果を見てから足した）：
設備投資額の合計は、業種ごとの増加を足したものより小さかった。電気業（発電所）の大きな減少が混ざっているためと見られる。
「製造業の国内回帰」を見るため、電気業・ガス業・熱供給業を除いた製造業だけで、件数・面積・設備投資額と、1件当たりの面積・設備投資額を比べる。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
D, RES = ROOT / "data", ROOT / "results"
r3 = lambda x: round(float(x), 3)
d = pd.read_csv(D / "ritchi_by_industry.csv", dtype={"code": str})
UT = ["電気業", "ガス業", "熱供給業"]
A, B = list(range(2015, 2020)), list(range(2021, 2026))
dl = lambda a, b: r3(100 * np.log(b / a))
rows = {}
for m in ["count", "area_1000m2", "capex_mil"]:
    x = d[d.measure == m]
    tot = x[x.code == "TOTAL"].set_index("year").value
    ut = x[x.name.isin(UT)].groupby("year").value.sum()
    rows[m] = pd.DataFrame({"total": tot, "utilities": ut, "manufacturing": tot - ut})
M = pd.concat({k: v.manufacturing for k, v in rows.items()}, axis=1)
M["area_per_site"] = M.area_1000m2 / M["count"]; M["capex_per_site"] = M.capex_mil / M["count"]
U = pd.concat({k: v.utilities for k, v in rows.items()}, axis=1)
M.round(4).to_csv(RES / "requestion_manufacturing_by_year.csv"); U.round(4).to_csv(RES / "requestion_utilities_by_year.csv")
out = {c: dict(avg_2015_19=r3(M.loc[A, c].mean()), avg_2021_25=r3(M.loc[B, c].mean()), dlog=dl(M.loc[A, c].mean(), M.loc[B, c].mean())) for c in M.columns}
out["utilities_capex"] = dict(avg_2015_19=r3(U.loc[A, "capex_mil"].mean()), avg_2021_25=r3(U.loc[B, "capex_mil"].mean()))
cap = d[(d.measure == "capex_mil") & ~d.name.isin(UT) & (d.code != "TOTAL") & (d.code != "old")].pivot_table(index="year", columns="name", values="value", aggfunc="sum")
ch = cap.loc[B].mean() - cap.loc[A].mean()
mch = M.loc[B, "capex_mil"].mean() - M.loc[A, "capex_mil"].mean()
out["manuf_capex_contrib_pct"] = {k: r3(100 * v / mch) for k, v in ch.sort_values(ascending=False).head(6).items()}
out["electronics_share_of_manuf_capex_2021_25"] = r3(100 * cap.loc[B, "電子･デバイス"].sum() / M.loc[B, "capex_mil"].sum())
out["ex_electronics_manuf_capex_dlog"] = dl((M.loc[A, "capex_mil"] - cap.loc[A, "電子･デバイス"]).mean(), (M.loc[B, "capex_mil"] - cap.loc[B, "電子･デバイス"]).mean())
(RES / "requestion.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(out, ensure_ascii=False, indent=0)); print(M.round(1).to_string()); print(U.round(0).to_string())

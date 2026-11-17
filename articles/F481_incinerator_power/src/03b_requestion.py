"""問い直し（結果を見てから足した）：2013→2024年度の発電の増加は、「新しくできた施設」と「なくなった施設」の入れ替えから来たのか、
「続いている施設」の発電の伸びから来たのか。施設コードで二つの年度をつなぐ。
施設コードは2013年度から入っているが、2020年度に書き方が変わった（13字→7字）ため、2013→2019年度と2020→2024年度の二つの期間に分けてつなぐ。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
f = pd.read_csv(ROOT / "data" / "facilities.csv", low_memory=False, dtype={"fac_code": str})
for c in ["tons", "gen_kw", "gen_mwh", "start_fy"]:
    f[c] = pd.to_numeric(f[c], errors="coerce").fillna(0.0)
cf = f.gen_mwh / (f.gen_kw / 1000 * 8784)
bad = (f.gen_kw > 0) & (cf > 10)
f.loc[bad, "gen_mwh"] = f.loc[bad, "gen_mwh"] / 1000  # 本線と同じ直し方


def side(fy):
    d = f[f.fy == fy].groupby("fac_code", sort=True).agg(gen=("gen_mwh", "sum"), tons=("tons", "sum"), kw=("gen_kw", "sum"))
    return d




def link(y0, y1):
    a, b = side(y0), side(y1)
    both = a.index.intersection(b.index)
    only_b = b.index.difference(a.index)
    only_a = a.index.difference(b.index)
    started = both[(a.loc[both, "gen"] == 0) & (b.loc[both, "gen"] > 0)]
    cont = both[(a.loc[both, "gen"] > 0) & (b.loc[both, "gen"] > 0)]
    total = float(b.gen.sum() - a.gen.sum())
    parts = {
        "続いている施設（両年とも発電）の増減": float((b.loc[cont, "gen"] - a.loc[cont, "gen"]).sum()),
        "続いている施設で発電を始めた分": float(b.loc[started, "gen"].sum()),
        "続いている施設で発電をやめた分": float(-a.loc[both[(a.loc[both, "gen"] > 0) & (b.loc[both, "gen"] == 0)], "gen"].sum()),
        "新しいコードの施設（新設・建て替え）": float(b.loc[only_b, "gen"].sum()),
        "なくなったコードの施設（廃止・建て替え）": float(-a.loc[only_a, "gen"].sum()),
    }
    ca, cb = a.loc[cont], b.loc[cont]
    return {
        "period": f"{y0}-{y1}", "total_change_gwh": round(total / 1000, 1),
        "parts_gwh": {k: round(v / 1000, 1) for k, v in parts.items()},
        "parts_share_pct": {k: round(v / total * 100, 1) for k, v in parts.items()},
        "n_both": int(len(both)), "n_only_end": int(len(only_b)), "n_only_start": int(len(only_a)),
        "n_only_end_gen": int((b.loc[only_b, "gen"] > 0).sum()), "n_only_start_gen": int((a.loc[only_a, "gen"] > 0).sum()),
        "n_continuing_gen": int(len(cont)), "n_started_gen": int(len(started)),
        "continuing_kwh_t_start": round(float(ca.gen.sum() * 1000 / ca.tons.sum()), 1),
        "continuing_kwh_t_end": round(float(cb.gen.sum() * 1000 / cb.tons.sum()), 1),
    }


res = [link(2013, 2019), link(2020, 2024)]
rows = []
for r in res:
    for k, v in r["parts_gwh"].items():
        rows.append({"period": r["period"], "part": k, "gwh": v, "share_of_change_pct": r["parts_share_pct"][k]})
pd.DataFrame(rows).to_csv(R / "requestion_entry_exit.csv", index=False)
new_share = [r["parts_share_pct"]["新しいコードの施設（新設・建て替え）"] + r["parts_share_pct"]["なくなったコードの施設（廃止・建て替え）"] for r in res]
out = {"links": res, "net_turnover_share_pct": [round(x, 1) for x in new_share],
       "note": "施設コードは建て替えで変わることがあるため、「新しいコード」には同じ場所の建て替えも含まれる（推測）。"}
json.dump(out, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))

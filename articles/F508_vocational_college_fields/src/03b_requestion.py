"""問い直し（結果を見てから足した）：2010→2025年度に工業・商業実務・文化・教養が増えたのは、どの学科（小区分）か。
学科の分類は2005年度以降そろっているので、2010・2025年度の専門課程で比べる。"""
import json
import pandas as pd
from common import DATA, RES, SHOWN, NAME

sd = pd.read_csv(DATA / "subfields_by_year.csv")
sd = sd[(sd.course == "senmon") & sd.field.isin(SHOWN)]
p = sd[sd.year.isin([2010, 2025])].pivot_table(index=["field", "sub"], columns="year", values="students", aggfunc="sum").fillna(0)
p["diff"] = p[2025] - p[2010]
p = p.reset_index()
p["field_name"] = p.field.map(NAME)
p = p.sort_values(["field", "sub"]).reset_index(drop=True)
p.rename(columns={2010: "y2010", 2025: "y2025"}).to_csv(RES / "requestion_subfields.csv", index=False)
q = {"note": "専門課程の学科（小区分）別生徒数、2010→2025年度。「その他」は各分野の中のその他。"}
for f in ("kogyo", "shogyo", "bunka", "eisei"):
    g = p[p.field == f]
    q[f] = {"field_diff": int(g["diff"].sum()),
            "subs": {r["sub"]: {"2010": int(r[2010]), "2025": int(r[2025]), "diff": int(r["diff"])} for _, r in g.iterrows()}}
named = p[p["sub"] != "その他"].sort_values("diff")
q["top_increase"] = [{"field": NAME[r.field], "sub": r["sub"], "diff": int(r["diff"]), "2010": int(r[2010]), "2025": int(r[2025])} for _, r in named.tail(5).iloc[::-1].iterrows()]
q["top_decrease"] = [{"field": NAME[r.field], "sub": r["sub"], "diff": int(r["diff"]), "2010": int(r[2010]), "2025": int(r[2025])} for _, r in named.head(5).iterrows()]
inc = p[p["diff"] > 0]["diff"].sum()
q["sum_increase_six"] = int(inc)
q["sum_decrease_six"] = int(p[p["diff"] < 0]["diff"].sum())
json.dump(q, open(RES / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps({k: q[k] for k in ["top_increase", "top_decrease", "sum_increase_six", "sum_decrease_six"]}, ensure_ascii=False, indent=0))
print(json.dumps(q["kogyo"], ensure_ascii=False)); print(json.dumps(q["shogyo"], ensure_ascii=False))

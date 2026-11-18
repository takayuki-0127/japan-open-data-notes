"""問い直し（結果を見てから足した）：上昇はいつ起きたのか。毎年の分解を足し上げ（連鎖）、期間ごとにまとめる。
あわせて、輸入の減少が丸太と製品のどちらか（供給量累年統計）を見る。"""
import json, pathlib, sys
import pandas as pd
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import RES, W, run

M = json.load(open(RES / "main.json", encoding="utf-8"))
a, b = M["y_min"], M["end"]
GROUPS = {"国内・用材": ["dom_seizai", "dom_gouhan", "dom_pulp", "dom_sonota"], "国内・燃料材": ["dom_nenryo"], "国内・しいたけ原木": ["dom_shiitake"],
          "輸入・用材": ["imp_seizai", "imp_gouhan", "imp_pulp", "imp_sonota"], "輸入・燃料材": ["imp_nenryo"]}
rows = []
for y in range(a, b):
    r = run(y, y + 1)
    rec = {"from": y, "to": y + 1, "change": r["change"]}
    for g, cols in GROUPS.items(): rec[g] = sum(r[c] for c in cols)
    rows.append(rec)
ann = pd.DataFrame(rows)
ann.round(4).to_csv(RES / "requestion_annual.csv", index=False)
PER = [(a, 2008), (2008, 2013), (2013, 2014), (2014, 2019), (2019, b)]
per = []
for p0, p1 in PER:
    s = ann[(ann["from"] >= p0) & (ann["to"] <= p1)]
    rec = {"period": f"{p0}→{p1}", "ss_from": float(W.loc[p0, "ss_total_pub"]), "ss_to": float(W.loc[p1, "ss_total_pub"]), "change": round(s.change.sum(), 3)}
    for g in GROUPS: rec[g] = round(s[g].sum(), 3)
    per.append(rec)
perdf = pd.DataFrame(per)
perdf.to_csv(RES / "requestion_periods.csv", index=False)
chain_total = float(ann.change.sum())
chain = {g: round(float(ann[g].sum()), 3) for g in GROUPS}

# 輸入の丸太・製品の別
imp = {k: {"from": float(W.loc[a, c]), "to": float(W.loc[b, c])} for k, c in
       [("丸太", "imp_maruta"), ("製品の計", "imp_prod_total"), ("製材品等", "imp_prod_seizaihin"), ("合板等", "imp_prod_gouhanhin"),
        ("木材パルプ", "imp_prod_pulphin"), ("木材チップ等", "imp_prod_chiphin"), ("その他", "imp_prod_sonotahin"), ("燃料材", "imp_nenryo")]}
out = {"chain_total_pt": round(chain_total, 3), "direct_total_pt": M["change_pt"], "chain_by_group": chain,
       "periods": per, "imports_form": imp,
       "jump_2013_2014": {"dom_nenryo_2013": float(W.loc[2013, "dom_nenryo"]), "dom_nenryo_2014": float(W.loc[2014, "dom_nenryo"]),
                          "ss_2013": float(W.loc[2013, "ss_total_pub"]), "ss_2014": float(W.loc[2014, "ss_total_pub"]),
                          "ss_youzai_2013": float(W.loc[2013, "ss_youzai_pub"]), "ss_youzai_2014": float(W.loc[2014, "ss_youzai_pub"])},
       "ss_2009": float(W.loc[2009, "ss_total_pub"]), "ss_2008": float(W.loc[2008, "ss_total_pub"]),
       "imp_total_2008": float(W.loc[2008, "imp_total"]), "imp_total_2009": float(W.loc[2009, "imp_total"])}
json.dump(out, open(RES / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(perdf.to_string()); print(chain, chain_total); print(json.dumps(imp, ensure_ascii=False))

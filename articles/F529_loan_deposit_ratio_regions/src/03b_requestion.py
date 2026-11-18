"""問い直し：預金の増加のうち、個人預金と、それ以外（法人など・公金・金融機関）のどちらが大きいか（オフライン）。"""
import json, pathlib, importlib.util
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("a", ROOT / "src" / "03_analysis.py"); a = importlib.util.module_from_spec(spec); spec.loader.exec_module(a)

def main():
    df = a.load(); g = a.fy_avg(df); w = a.units_table(g)
    rows = []
    for f, t in ((1998, 2025), (2022, 2025)):
        for u in a.UNITS + ["全国"]:
            x = {k: w.xs(k, level="item")[u] for k in ("deposits", "general", "personal", "public", "fin", "loans")}
            dD = x["deposits"][t] - x["deposits"][f]
            parts = {"個人預金": x["personal"][t] - x["personal"][f],
                     "法人などの預金（一般預金−個人預金）": (x["general"][t] - x["personal"][t]) - (x["general"][f] - x["personal"][f]),
                     "公金預金": x["public"][t] - x["public"][f], "金融機関預金": x["fin"][t] - x["fin"][f]}
            parts["その他（政府関係預り金など）"] = dD - sum(parts.values())
            for k, v in parts.items():
                rows.append({"from": f, "to": t, "unit": u, "part": k, "increase_oku": round(float(v), 1), "share_of_deposit_increase": round(float(v / dD), 4),
                             "deposit_increase_oku": round(float(dD), 1), "loan_increase_oku": round(float(x["loans"][t] - x["loans"][f]), 1)})
    t = pd.DataFrame(rows); t.to_csv(ROOT / "results" / "requestion_deposit_parts.csv", index=False)
    p98 = t[(t["from"] == 1998)].pivot(index="unit", columns="part", values="share_of_deposit_increase")
    out = {"personal_share_98_25": {u: round(float(p98.loc[u, "個人預金"]) * 100, 1) for u in a.UNITS + ["全国"]},
           "corp_share_98_25": {u: round(float(p98.loc[u, "法人などの預金（一般預金−個人預金）"]) * 100, 1) for u in a.UNITS + ["全国"]},
           "personal_share_98_25_median_excl_tokyo": round(float(p98.loc[[u for u in a.UNITS if u != "東京"], "個人預金"].median()) * 100, 1)}
    nat = t[(t.unit == "全国") & (t["from"] == 1998)].set_index("part")
    out["national_98_25_tn"] = {k: round(float(v) / 1e4, 1) for k, v in nat.increase_oku.items()}
    out["national_deposit_increase_98_25_tn"] = round(float(nat.deposit_increase_oku.iloc[0]) / 1e4, 1)
    out["national_loan_increase_98_25_tn"] = round(float(nat.loan_increase_oku.iloc[0]) / 1e4, 1)
    m = json.loads((ROOT / "results" / "main.json").read_text(encoding="utf-8"))
    m["requestion"] = out
    (ROOT / "results" / "main.json").write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=0))

if __name__ == "__main__":
    main()

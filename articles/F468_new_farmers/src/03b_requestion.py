"""問い直し（結果を見てから足した）：49歳以下が最も多かった年から最新の年までの減少は、どの形のどの年齢で起きたか。
形（自営・雇用・参入）×年齢（15〜39歳、40〜49歳）の人数の差に分ける（足すと一致）。あわせて、各形のうち49歳以下の割合。"""
import json, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES = ROOT / "results"
N = pd.read_csv(ROOT / "data" / "new_farmers.csv")
M = json.load(open(RES / "main.json", encoding="utf-8"))
a, b = M["y49_peak"], M["end"]
FL = {"jiei": "新規自営農業就農者", "koyo": "新規雇用就農者", "sannyu": "新規参入者"}
rows = []
for f, lab in FL.items():
    e = N[N.form == f].set_index("year")
    for col, al in [("le39", "15〜39歳"), ("a40_49", "40〜49歳")]:
        rows.append({"form": lab, "age": al, "from": float(e.loc[a, col]), "to": float(e.loc[b, col]), "change": float(e.loc[b, col] - e.loc[a, col])})
df = pd.DataFrame(rows)
df["share_of_change"] = (df.change / df.change.sum()).round(4)
df.to_csv(RES / "requestion_le49_form_age.csv", index=False)
sh = []
for f, lab in FL.items():
    e = N[N.form == f].set_index("year")
    for y in [2007, 2010, a, b]:
        sh.append({"form": lab, "year": y, "le49_share_in_form": round(100 * e.loc[y, "le49"] / e.loc[y, "all"], 2)})
sh = pd.DataFrame(sh); sh.to_csv(RES / "requestion_le49_share_by_form.csv", index=False)
out = {"from": a, "to": b, "total_change": float(df.change.sum()), "rows": rows, "le49_share_by_form": sh.to_dict("records")}
json.dump(out, open(RES / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(df.to_string()); print(sh.pivot(index="form", columns="year", values="le49_share_in_form"))

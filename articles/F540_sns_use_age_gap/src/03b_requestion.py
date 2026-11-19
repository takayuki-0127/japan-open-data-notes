"""問い直し（結果を見てから足した）：選択肢が変わった2つの年（2019→2020、2020→2021）を除くと、
20代と70代の差はどれだけ縮んだのか。差の変化（2015→2025）を「変わった年」と「それ以外の年」に分ける。"""
import json, pathlib
import pandas as pd

BASE = pathlib.Path(__file__).resolve().parent.parent
RES = BASE / "results"
df = pd.read_csv(BASE / "data" / "panel.csv")
CHANGE_YEARS = [2020, 2021]  # 前の年からの変化が、選択肢の変わり目にあたる年


def wide(col):
    return df[df.sex == "計"].pivot(index="year", columns="age", values=col)


out, rows = {}, []
for col, lab in [("p_all", "人口ベース"), ("s", "利用者ベース")]:
    w = wide(col)
    gap = (w["20-29"] - w["70-79"]).loc[2015:2025]
    d = gap.diff().dropna()
    chg = d.loc[CHANGE_YEARS].sum()
    other = d.drop(CHANGE_YEARS).sum()
    total = gap.loc[2025] - gap.loc[2015]
    out[col] = {"gap_2015": round(gap.loc[2015], 1), "gap_2025": round(gap.loc[2025], 1), "total_change": round(total, 1),
                "change_years": round(chg, 1), "other_years": round(other, 1), "share_change_years": round(chg / total, 3),
                "gap_2025_if_no_change_years": round(gap.loc[2015] + other, 1)}
    for y, v in d.items():
        rows.append({"base": lab, "year": int(y), "d_gap": round(v, 2), "change_year": y in CHANGE_YEARS})
    # 70代の s の伸びのうち、変わり目の2年が占める割合
    s70 = wide("s")["70-79"].loc[2015:2025].diff().dropna()
    out[f"{col}_70s_s_growth"] = {"total": round(s70.sum(), 1), "change_years": round(s70.loc[CHANGE_YEARS].sum(), 1)}

pd.DataFrame(rows).to_csv(RES / "requestion_gap_changes.csv", index=False)
ws = wide("s")
jump = {a: {"d_2019_2020": round(ws.loc[2020, a] - ws.loc[2019, a], 1), "d_2020_2021": round(ws.loc[2021, a] - ws.loc[2020, a], 1)} for a in ws.columns}
out["s_jumps"] = jump
(RES / "requestion.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
print(json.dumps(out, ensure_ascii=False, indent=1))

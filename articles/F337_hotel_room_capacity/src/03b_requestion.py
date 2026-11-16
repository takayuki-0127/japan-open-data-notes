"""問い直し（結果を見てから足した）：
年平均の稼働率は2025年が2019年より低かった。では、混む月の稼働率はどうか。
2019・2023・2024・2025年の第8表の月別（1〜12月）から、全国の客室稼働率（全体・シティホテル・ビジネスホテル）を取り出し、最も高い月の値と、70%以上の月の数を比べる。"""
import json, pathlib, re, warnings
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW, RES = ROOT / "data" / "raw", ROOT / "results"
r3 = lambda x: round(float(x), 3)
def norm(s): return re.sub(r"[\s\n]", "", str(s)) if pd.notna(s) else ""
def national(path, sheet, targets):
    v = pd.read_excel(path, sheet_name=sheet, header=None)
    row = next(i for i in range(4, 15) if (norm(v.iloc[i, 0]).startswith("全国") or re.search(r"\d+月$", norm(v.iloc[i, 0]))) and pd.notna(pd.to_numeric(v.iloc[i, 1], errors="coerce")))
    out = {"all": float(v.iloc[row, 1])}
    for j in range(2, v.shape[1]):
        h = [norm(v.iloc[i, j]) for i in range(3, row)]
        for t in targets:
            if t not in out and any(x.startswith(t) for x in h): out[t] = float(v.iloc[row, j])
    return out
recs = []
for y in [2019, 2023, 2024, 2025]:
    p = next(RAW.glob(f"shukuhaku_{y}.xls*"))
    for mth in range(1, 13):
        o = national(p, f"第8表({mth}月)", ["シティホテル", "ビジネスホテル"])
        recs.append(dict(year=y, month=mth, **o))
m = pd.DataFrame(recs); m.to_csv(RES / "requestion_monthly_occupancy.csv", index=False)
out = {}
for col in ["all", "シティホテル", "ビジネスホテル"]:
    out[col] = {int(y): dict(max=r3(g[col].max()), max_month=int(g.loc[g[col].idxmax(), "month"]), months_ge70=int((g[col] >= 70).sum()), months_ge80=int((g[col] >= 80).sum())) for y, g in m.groupby("year")}
(RES / "requestion.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(out, ensure_ascii=False, indent=0))

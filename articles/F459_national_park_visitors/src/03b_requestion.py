"""問い直し（結果を見てから足した）：国立公園の利用者は2019年より減ったが、訪日客の利用（環境省の推計、参考値）はどう動いたか。"""
import json, pathlib, re, unicodedata
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
R = ROOT / "results"
n = lambda s: re.sub(r"[\s　]", "", unicodedata.normalize("NFKC", str(s))) if isinstance(s, str) else ""
v = pd.read_excel(ROOT / "data" / "raw" / "naturalpark_12.xlsx", header=None)
YC = {4: 2016, 6: 2017, 8: 2018, 10: 2019, 18: 2023, 20: 2024}
row = next(i for i in range(len(v)) if n(v.iloc[i, 3]) == "(実利用者数)")
rate = next(i for i in range(len(v)) if n(v.iloc[i, 1]).startswith("訪問率"))
tot = next(i for i in range(len(v)) if n(v.iloc[i, 1]).startswith("訪日外客数"))
s = pd.read_csv(R / "series.csv", index_col="year")
rows = []
for j, y in YC.items():
    rows.append(dict(year=y, foreign_users=float(v.iloc[row, j]), visit_rate=float(v.iloc[rate, j]), inbound_total=float(v.iloc[tot, j]),
                     np_users=float(s.loc[y, "np_10k"]) * 1e4))
f = pd.DataFrame(rows).set_index("year")
f["foreign_share_pct"] = f.foreign_users / f.np_users * 100
f.to_csv(R / "requestion_foreign.csv", float_format="%.4f")
out = {"foreign_2019": round(float(f.loc[2019, "foreign_users"])), "foreign_2024": round(float(f.loc[2024, "foreign_users"])),
       "foreign_pct_2019_2024": round(float(f.loc[2024, "foreign_users"] / f.loc[2019, "foreign_users"] * 100 - 100), 1),
       "rate_2019": round(float(f.loc[2019, "visit_rate"]) * 100, 1), "rate_2024": round(float(f.loc[2024, "visit_rate"]) * 100, 1),
       "share_2019": round(float(f.loc[2019, "foreign_share_pct"]), 2), "share_2024": round(float(f.loc[2024, "foreign_share_pct"]), 2),
       "foreign_2016": round(float(f.loc[2016, "foreign_users"]))}
json.dump(out, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
print(out)

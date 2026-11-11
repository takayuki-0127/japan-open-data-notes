"""01 取得：元データの確認（新しい取得はしない）
- data/lodging_pref_monthly_2011_2025.csv : 観光庁「宿泊旅行統計調査」推移表（F98・F240 と同じ表）
- data/pref_population_ssdse_b.csv : 統計センター SSDSE-B-2026 の都道府県別総人口（F183 と同じ）
"""
import hashlib, json, pathlib
D = pathlib.Path(__file__).resolve().parents[1] / "data"
out = {}
for f in ["lodging_pref_monthly_2011_2025.csv", "pref_population_ssdse_b.csv"]:
    b = (D / f).read_bytes()
    out[f] = {"bytes": len(b), "md5": hashlib.md5(b).hexdigest()}
print(json.dumps(out, ensure_ascii=False, indent=1))
(D.parent / "results" / "manifest.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))

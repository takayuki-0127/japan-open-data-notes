"""F293 01 取得：新しい取得はしない。前の記事のデータの写しを data/raw に置き、md5 を記録する。

- s1_shogyo_6types.csv        … F231（商業動態統計 業態別販売額、2014-01〜2026-08）
- s2_cpi_items_monthly.csv.gz … F209（消費者物価指数 品目、全国、2020年基準、2015-01〜2026-09）
- s2_cpi_items_meta.csv       … F209（品目の名前・符号・ウエイト）
- kakei_items_monthly_2015_2026.csv, kakei_3X7_2025_2026.csv … F283（家計調査 品目別支出、二人以上の世帯）
"""
import hashlib, json, pathlib
BASE = pathlib.Path(__file__).resolve().parents[1]
RAW = BASE / "data" / "raw"
man = {p.name: hashlib.md5(p.read_bytes()).hexdigest() for p in sorted(RAW.iterdir()) if p.is_file()}
old = BASE / "data" / "MANIFEST.json"
if old.exists():
    prev = json.loads(old.read_text())
    for k, v in prev.items():
        assert man.get(k) == v, f"md5 が違う: {k}"
    print("md5 OK", len(prev))
else:
    old.write_text(json.dumps(man, ensure_ascii=False, indent=1))
    print("MANIFEST を書いた", len(man))

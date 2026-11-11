"""F294 取得: data/raw のファイルの出典URLとmd5を記録する。
ファイルはブラウザで出典から取得し data/raw に置いた（取得日 2026-11-12）。
"""
import hashlib, json, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
URLS = {
    "kyufu14_09.xls": "https://www.mhlw.go.jp/toukei/saikin/hw/kaigo/kyufu/14/dl/09.xls",
    "kyufu19_09.xlsx": "https://www.mhlw.go.jp/toukei/saikin/hw/kaigo/kyufu/19/dl/09.xlsx",
    "kyufu24_09.xlsx": "https://www.mhlw.go.jp/toukei/saikin/hw/kaigo/kyufu/24/dl/09.xlsx",
    "kyufu25_09.xlsx": "https://www.mhlw.go.jp/toukei/saikin/hw/kaigo/kyufu/25/dl/09.xlsx",
    "ipss_1-9A.xlsx": "https://www.ipss.go.jp/pp-zenkoku/j/zenkoku2023/db_zenkoku2023/s_tables/1-9a.xlsx",
    "ipss_4-9A.xlsx": "https://www.ipss.go.jp/pp-zenkoku/j/zenkoku2023/db_zenkoku2023/s_tables/4-9A.xlsx",
    "ipss_7-9A.xlsx": "https://www.ipss.go.jp/pp-zenkoku/j/zenkoku2023/db_zenkoku2023/s_tables/7-9A.xlsx",
}
rows = []
for name, url in URLS.items():
    p = RAW / name
    rows.append({"file": name, "url": url, "bytes": p.stat().st_size,
                 "md5": hashlib.md5(p.read_bytes()).hexdigest()})
(RAW / "manifest.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
for r in rows:
    print(r["file"], r["bytes"], r["md5"])

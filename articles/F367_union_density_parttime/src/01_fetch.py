"""01_fetch.py : 公式サイト（e-Stat）から元データを取得して data/raw/ に保存する。
ネットが必要。run_all.sh からは呼ばない（data/raw に同梱済み）。

取得元：厚生労働省「労働組合基礎調査」時系列表（令和7年調査まで）
- 第1表 労働組合種類別労働組合数、労働組合員数及び推定組織率の推移
- 第3表 企業規模別単位労働組合数及び労働組合員数
- 第8表 パートタイム労働者の単位労働組合員数及び推定組織率の推移
"""
import hashlib
import pathlib
import time
import urllib.request

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)
EST = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=4"
FILES = [("ts1_members_density", "000008644119"), ("ts3_by_firm_size", "000008644121"), ("ts8_parttime", "000008644126")]


def main():
    rows = []
    for stem, sid in FILES:
        with urllib.request.urlopen(urllib.request.Request(EST.format(sid)), timeout=180) as r:
            disp = r.headers.get("Content-Disposition", "")
            b = r.read()
        (RAW / (stem + ".xlsx")).write_bytes(b)
        rows.append((stem + ".xlsx", sid, 4, len(b), hashlib.sha256(b).hexdigest()[:12], disp))
        print(stem, len(b))
        time.sleep(1)
    with open(RAW / "fetch_log.tsv", "w", encoding="utf-8") as f:
        f.write("file\tstatInfId\tfileKind\tbytes\tsha256_12\tcontent_disposition\n")
        for r in rows:
            f.write("\t".join(map(str, r)) + "\n")


if __name__ == "__main__":
    main()

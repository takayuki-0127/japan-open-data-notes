"""01_fetch.py : 公式サイト（e-Stat）から元データを取得して data/raw/ に保存する。
ネットが必要。run_all.sh からは呼ばない（data/raw に同梱済み）。

取得元
- 総務省「労働力調査」年報 詳細集計 全国・時系列表「年齢階級，現職の雇用形態についた主な理由別非正規の職員・従業員数」
  2017年版（2013〜2017年）、2022年版（2018〜2022年）、2025年版（2021〜2025年）
- 厚生労働省「一般職業紹介状況」長期時系列表 3 有効求人倍率（パートを含む、実数・季節調整値）
"""
import hashlib
import pathlib
import time
import urllib.request

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)
EST = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind={}"
FILES = [
    ("lfs_reason_2013_2017", "000031702919", 0),
    ("lfs_reason_2018_2022", "000040058529", 0),
    ("lfs_reason_2021_2025", "000040440965", 0),
    ("jobs_to_applicants_ratio_longterm", "000040518983", 0),
]


def main():
    rows = []
    for stem, sid, kind in FILES:
        with urllib.request.urlopen(urllib.request.Request(EST.format(sid, kind)), timeout=180) as r:
            disp = r.headers.get("Content-Disposition", "")
            b = r.read()
        ext = ".xls" if b[:4] == b"\xd0\xcf\x11\xe0" else ".xlsx"
        (RAW / (stem + ext)).write_bytes(b)
        rows.append((stem + ext, sid, kind, len(b), hashlib.sha256(b).hexdigest()[:12], disp))
        print(stem + ext, len(b))
        time.sleep(1)
    with open(RAW / "fetch_log.tsv", "w", encoding="utf-8") as f:
        f.write("file\tstatInfId\tfileKind\tbytes\tsha256_12\tcontent_disposition\n")
        for r in rows:
            f.write("\t".join(map(str, r)) + "\n")


if __name__ == "__main__":
    main()

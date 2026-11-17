"""01_fetch.py : 公式サイト（e-Stat）から元データを取得して data/raw/ に保存する。
ネットが必要。run_all.sh からは呼ばない（data/raw に同梱済み）。

取得元：総務省「家計調査」家計収支編 二人以上の世帯 年報
- 2013・2014・2015・2023・2024年：＜品目分類＞1世帯当たり年間の品目別支出金額，購入数量及び平均価格
  （時系列、年間収入五分位階級別、世帯主の年齢階級別）食料「調理食品」～「飲料」
- 2025年：＜品目分類＞第4-6表 世帯主の年齢階級別1世帯当たり年間の支出金額，購入数量及び平均価格
"""
import hashlib
import pathlib
import time
import urllib.request

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)
EST = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind={}"
FILES = [
    ("fies_2013_beverages", "000025408559", 0),
    ("fies_2014_beverages", "000030057509", 0),
    ("fies_2015_beverages", "000031418120", 0),
    ("fies_2023_beverages", "000040193337", 4),
    ("fies_2024_beverages", "000040297524", 4),
    ("fies_2025_age_4_6", "000040409549", 0),
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

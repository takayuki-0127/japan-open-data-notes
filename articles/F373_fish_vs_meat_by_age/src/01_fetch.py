"""01_fetch.py : 公式サイト（e-Stat）から元データを取得して data/raw/ に保存する。
ネットが必要。run_all.sh からは呼ばない（data/raw に同梱済み）。

取得元：総務省「家計調査」家計収支編 二人以上の世帯 年報
- 2013〜2024年：＜品目分類＞1世帯当たり年間の品目別支出金額，購入数量及び平均価格
  （時系列、年間収入五分位階級別、世帯主の年齢階級別）食料「魚介類」、食料「肉類～乳卵類」
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
    ("fies_2013_fish", "000025408554", 0),
    ("fies_2013_meat", "000025408555", 0),
    ("fies_2014_fish", "000030057504", 0),
    ("fies_2014_meat", "000030057505", 0),
    ("fies_2015_fish", "000031418115", 0),
    ("fies_2015_meat", "000031418116", 0),
    ("fies_2016_fish", "000031586351", 0),
    ("fies_2016_meat", "000031586352", 0),
    ("fies_2017_fish", "000031705224", 0),
    ("fies_2017_meat", "000031705225", 0),
    ("fies_2018_fish", "000031828435", 0),
    ("fies_2018_meat", "000031828496", 0),
    ("fies_2019_fish", "000031964787", 0),
    ("fies_2019_meat", "000031964788", 0),
    ("fies_2020_fish", "000032106562", 4),
    ("fies_2020_meat", "000032106563", 4),
    ("fies_2021_fish", "000032220969", 4),
    ("fies_2021_meat", "000032220970", 4),
    ("fies_2022_fish", "000040079002", 4),
    ("fies_2022_meat", "000040079003", 4),
    ("fies_2023_fish", "000040193332", 4),
    ("fies_2023_meat", "000040193333", 4),
    ("fies_2024_fish", "000040297519", 4),
    ("fies_2024_meat", "000040297520", 4),
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

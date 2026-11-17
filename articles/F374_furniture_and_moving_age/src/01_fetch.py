"""01_fetch.py : 公式サイト（e-Stat）から元データを取得して data/raw/ に保存する。
ネットが必要。run_all.sh からは呼ばない（data/raw に同梱済み）。

取得元
- 総務省「家計調査」家計収支編 二人以上の世帯 年報 2013〜2024年：＜品目分類＞1世帯当たり年間の品目別支出金額，
  購入数量及び平均価格（時系列、月別、年間収入五分位階級別、世帯主の年齢階級別）家具・家事用品
- 同 2025年：第4-6表 世帯主の年齢階級別1世帯当たり年間の支出金額，購入数量及び平均価格
- 総務省「住民基本台帳人口移動報告」長期時系列表 第1表（月別の都道府県内・都道府県間移動者数）、
  2024年 年齢（5歳階級）別の都道府県内移動率・他都道府県への転出者の移動率
"""
import hashlib
import pathlib
import time
import urllib.request

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)
EST = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind={}"
FILES = [
    ("fies_2013_furn", "000025408562", 0),
    ("fies_2014_furn", "000030057512", 0),
    ("fies_2015_furn", "000031418123", 0),
    ("fies_2016_furn", "000031586359", 0),
    ("fies_2017_furn", "000031705232", 0),
    ("fies_2018_furn", "000031828503", 0),
    ("fies_2019_furn", "000031964795", 0),
    ("fies_2020_furn", "000032106630", 4),
    ("fies_2021_furn", "000032220977", 4),
    ("fies_2022_furn", "000040079010", 4),
    ("fies_2023_furn", "000040193340", 4),
    ("fies_2024_furn", "000040297527", 4),
    ("fies_2025_age_4_6", "000040409549", 0),
    ("moves_long_t1", "000040430814", 0),
    ("moves_rate_within_pref_2024", "000040270112", 0),
    ("moves_rate_out_pref_2024", "000040270110", 0),
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

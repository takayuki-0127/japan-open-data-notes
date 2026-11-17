"""01_fetch.py : 公式サイト（e-Stat）から元データを取得して data/raw/ に保存する。
ネットが必要。run_all.sh からは呼ばない（data/raw に同梱済み）。

取得元：総務省「労働力調査」基本集計 第IV-7表
「妻及び夫の就業状態・農林業・非農林業・従業上の地位・月末1週間の就業時間・月間就業時間，世帯の家族類型別夫婦のいる世帯数」（年平均）
- 2018〜2025年：2020年国勢調査基準（公表資料、時系列接続用を含む）
- 2016・2017年と2018〜2021年：旧基準（2010年・2015年国勢調査基準）。基準の違いによる段差の確かめに使う
"""
import hashlib
import pathlib
import time
import urllib.request

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)
EST = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind={}"
FILES = [
    ("iv7_2018_cur", "000032174009"), ("iv7_2019_cur", "000032174157"), ("iv7_2020_cur", "000032174233"),
    ("iv7_2021_cur", "000032173861"), ("iv7_2022_cur", "000040008584"), ("iv7_2023_cur", "000040137583"),
    ("iv7_2024_cur", "000040243384"), ("iv7_2025_cur", "000040403953"),
    ("iv7_2016_old2010", "000031524913"), ("iv7_2017_old2015", "000031667373"), ("iv7_2018_old2015", "000031789379"),
    ("iv7_2019_old2015", "000031905273"), ("iv7_2020_old2015", "000032045573"), ("iv7_2021_old2015", "000032164204"),
]


def main():
    rows = []
    for stem, sid in FILES:
        with urllib.request.urlopen(urllib.request.Request(EST.format(sid, 0)), timeout=180) as r:
            disp = r.headers.get("Content-Disposition", "")
            b = r.read()
        ext = ".xls" if b[:4] == b"\xd0\xcf\x11\xe0" else (".xlsx" if b[:2] == b"PK" else ".csv")
        (RAW / (stem + ext)).write_bytes(b)
        rows.append((stem + ext, sid, 0, len(b), hashlib.sha256(b).hexdigest()[:12], disp))
        print(stem + ext, len(b))
        time.sleep(1)
    with open(RAW / "fetch_log.tsv", "w", encoding="utf-8") as f:
        f.write("file\tstatInfId\tfileKind\tbytes\tsha256_12\tcontent_disposition\n")
        for r in rows:
            f.write("\t".join(map(str, r)) + "\n")


if __name__ == "__main__":
    main()

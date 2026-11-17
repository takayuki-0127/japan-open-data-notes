"""01_fetch.py : 公式サイト（e-Stat）から元データを取得して data/raw/ に保存する（F360 と同じファイル）。
ネットが必要。run_all.sh からは呼ばない（data/raw に同梱済み）。

取得元：厚生労働省「賃金構造基本統計調査」（e-Stat）
- 一般労働者 産業大分類 第1表（学歴、年齢階級別 所定内給与額など、産業計を使う）2006〜2025年
  （2006〜2019年は【参考掲載】の同じ推計方法による集計）
"""
import hashlib
import pathlib
import time
import urllib.request

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)
EST = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind={}"

GENERAL = {
    2006: ("000032135300", 4), 2007: ("000032135238", 4), 2008: ("000032135176", 4),
    2009: ("000032134932", 4), 2010: ("000032111802", 4), 2011: ("000032111754", 4),
    2012: ("000032111706", 4), 2013: ("000032111658", 4), 2014: ("000032111610", 4),
    2015: ("000032110750", 4), 2016: ("000032110710", 4), 2017: ("000032110670", 4),
    2018: ("000032110630", 4), 2019: ("000032110590", 4), 2020: ("000032069350", 0),
    2021: ("000032182871", 4), 2022: ("000040029100", 4), 2023: ("000040163660", 4),
    2024: ("000040247773", 4), 2025: ("000040420843", 4),
}


def get(sid, kind):
    req = urllib.request.Request(EST.format(sid, kind))
    with urllib.request.urlopen(req, timeout=180) as r:
        name = r.headers.get("Content-Disposition", "")
        b = r.read()
    time.sleep(1)
    return b, name


def main():
    rows = []
    jobs = [(f"general_{y}", *v) for y, v in GENERAL.items()]
    for stem, sid, kind in jobs:
        b, disp = get(sid, kind)
        ext = ".xls" if b[:4] == b"\xd0\xcf\x11\xe0" else ".xlsx"
        (RAW / (stem + ext)).write_bytes(b)
        rows.append((stem + ext, sid, kind, len(b), hashlib.sha256(b).hexdigest()[:12], disp))
        print(stem + ext, len(b))
    with open(RAW / "fetch_log.tsv", "w", encoding="utf-8") as f:
        f.write("file\tstatInfId\tfileKind\tbytes\tsha256_12\tcontent_disposition\n")
        for r in rows:
            f.write("\t".join(map(str, r)) + "\n")


if __name__ == "__main__":
    main()

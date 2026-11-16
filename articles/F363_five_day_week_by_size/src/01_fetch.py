"""01_fetch.py : 公式サイト（e-Stat）から元データを取得して data/raw/ に保存する。
ネットが必要。run_all.sh からは呼ばない（data/raw に同梱済み）。

取得元：厚生労働省「就労条件総合調査」各年の「企業規模、産業、主な週休制の形態別企業（数）割合」
（2001〜2025年の調査、各年1月1日現在）
"""
import hashlib
import pathlib
import time
import urllib.request

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)
EST = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind={}"
FILES = {  # 調査年: (statInfId, fileKind)
    2001: ("000002023414", 0), 2002: ("000002021317", 0), 2003: ("000002018060", 0), 2004: ("000002015078", 0),
    2005: ("000002012903", 0), 2006: ("000001211483", 0), 2007: ("000001211126", 0), 2008: ("000002042594", 0),
    2009: ("000008315386", 0), 2010: ("000008549744", 0), 2011: ("000012674008", 0), 2012: ("000018609700", 0),
    2013: ("000023628201", 0), 2014: ("000028691896", 0), 2015: ("000031362354", 0), 2016: ("000031605916", 0),
    2017: ("000031692591", 0), 2018: ("000031778230", 0), 2019: ("000031898902", 0), 2020: ("000032034516", 4),
    2021: ("000040009048", 4), 2022: ("000040013084", 4), 2023: ("000040149745", 4), 2024: ("000040260711", 4),
    2025: ("000040425669", 4),
}


def main():
    rows = []
    for y, (sid, kind) in FILES.items():
        with urllib.request.urlopen(urllib.request.Request(EST.format(sid, kind)), timeout=180) as r:
            disp = r.headers.get("Content-Disposition", "")
            b = r.read()
        ext = ".xls" if b[:4] == b"\xd0\xcf\x11\xe0" else ".xlsx"
        name = f"weekly_holiday_{y}{ext}"
        (RAW / name).write_bytes(b)
        rows.append((name, sid, kind, len(b), hashlib.sha256(b).hexdigest()[:12], disp))
        print(name, len(b))
        time.sleep(1)
    with open(RAW / "fetch_log.tsv", "w", encoding="utf-8") as f:
        f.write("file\tstatInfId\tfileKind\tbytes\tsha256_12\tcontent_disposition\n")
        for r in rows:
            f.write("\t".join(map(str, r)) + "\n")


if __name__ == "__main__":
    main()

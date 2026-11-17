"""01_fetch.py : 公式サイト（e-Stat）から元データを取得して data/raw/ に保存する。
ネットが必要。run_all.sh からは呼ばない（data/raw に同梱済み）。

取得元：総務省「労働力調査」
- 年報 詳細集計 全国・時系列表「年齢階級別未活用労働指標」（LU1〜LU4 と補助指標、男女別。各年版に直近5年の値と、その年の年齢階級別）
  2019年版〜2025年版（2019年版に2018年の値もある）
- 長期時系列表 1-e-3「未活用労働指標１（季節調整値及び原数値）2002年1月〜」（月次）
"""
import hashlib
import pathlib
import time
import urllib.request

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)
EST = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"
FILES = [("lu_annual_2019", "000031952662"), ("lu_annual_2020", "000032089806"),
         ("lu_annual_2021", "000032205617"), ("lu_annual_2022", "000040058536"), ("lu_annual_2023", "000040169078"),
         ("lu_annual_2024", "000040267875"), ("lu_annual_2025", "000040440972"), ("lu1_monthly_longterm", "000040254271")]


def main():
    rows = []
    for stem, sid in FILES:
        with urllib.request.urlopen(urllib.request.Request(EST.format(sid)), timeout=180) as r:
            disp = r.headers.get("Content-Disposition", "")
            b = r.read()
        ext = ".xls" if b[:4] == b"\xd0\xcf\x11\xe0" else ".xlsx"
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

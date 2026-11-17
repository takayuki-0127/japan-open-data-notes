"""01_fetch.py : 公式サイト（e-Stat）から元データを取得して data/raw/ に保存する。
ネットが必要。run_all.sh からは呼ばない（data/raw に同梱済み）。

取得元：総務省「労働力調査」長期時系列データ（詳細集計）
- 年平均 10-1 年齢階級（10歳階級）別就業者数及び年齢階級（10歳階級）、雇用形態別雇用者数（2002年〜、男女別）
- 四半期平均 9-1 同（四半期、2002年1〜3月期〜）
"""
import hashlib
import pathlib
import time
import urllib.request

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)
EST = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"
FILES = [("lfs_detail_10_1_annual", "000021915917"), ("lfs_detail_9_1_quarterly", "000021915916")]


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

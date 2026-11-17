"""01_fetch.py : 公式サイト（e-Stat）から元データを取得して data/raw/ に保存する。
ネットが必要。run_all.sh からは呼ばない（data/raw に同梱済み）。

取得元：厚生労働省「雇用均等基本調査」事業所調査
- 各年度の「育児休業者割合」（産業・事業所規模別、女性・男性）2009〜2025年度
  （2013年度は同じ名前の表が2つあり、e-Stat で後に載った「事_第３表」を使う。男性の値は2つの表で同じ）
- 「取得期間別育児休業後復職者割合」（男女計・女性・男性、産業・事業所規模別）2012・2015・2018・2021・2023・2025年度
"""
import hashlib
import pathlib
import time
import urllib.request

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)
EST = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"
RATE = {2009: "000014304215", 2010: "000012661483", 2011: "000017074209", 2012: "000023607058", 2013: "000027398626",
        2014: "000031335425", 2015: "000031495825", 2016: "000031642935", 2017: "000031773438", 2018: "000031852424",
        2019: "000031969779", 2020: "000032108530", 2021: "000032218460", 2022: "000040082762", 2023: "000040194862",
        2024: "000040302154", 2025: "000040480880"}
PERIOD = {2012: "000023607062", 2015: "000031495830", 2018: "000031852467", 2021: "000032218463", 2023: "000040194865",
          2025: "000040480884"}


def main():
    rows = []
    jobs = [(f"leave_rate_{y}", s) for y, s in RATE.items()] + [(f"leave_period_{y}", s) for y, s in PERIOD.items()]
    for stem, sid in jobs:
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

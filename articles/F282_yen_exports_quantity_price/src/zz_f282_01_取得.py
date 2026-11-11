"""01 取得：元データの出どころと MD5 を確かめる。

元データは data/raw に置いてある（2026-11-11 取得）。取り直すときは下の URL から同じ名前で保存する。
- 財務省「貿易統計」貿易指数の推移表（e-Stat、年ごとの CSV、2020年=100）
  https://www.e-stat.go.jp/stat-search/file-download?statInfId=<ID>&fileKind=1
  ID は STATINF に記した（2009〜2026年分）。
- 日本銀行 時系列統計データ API（https://www.stat-search.boj.or.jp/api/v1/getDataCode）
  PR01：PRCG20_2400000000（輸出物価・円ベース 総平均）、PRCG20_2300000000（契約通貨ベース）、類別7つ（PRCG20_24/23 00k20001）
  FM08：FXERM07（ドル円 東京17時 月中平均）　FM09：FX180110001・FX180110002（名目・実質実効為替レート）
- 財務省「貿易取引通貨別比率」輸出 https://www.customs.go.jp/toukei/shinbun/tuuka/timeseriesSCT_e.csv
"""
import hashlib, pathlib, sys
STATINF = {2026: "000040519596", 2025: "000040425361", 2024: "000040481201", 2023: "000040223724",
           2022: "000040117936", 2021: "000032255229", 2020: "000032046147", 2019: "000031927797",
           2018: "000031927798", 2017: "000031927799", 2016: "000031927800", 2015: "000031927801",
           2014: "000031750266", 2013: "000031750278", 2012: "000031750290", 2011: "000031750302",
           2010: "000031750314", 2009: "000031750326"}
RAW = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"
bad = 0
for ln in (RAW / "MD5.txt").read_text().splitlines():
    h, name = ln.split()
    got = hashlib.md5((RAW / name).read_bytes()).hexdigest()
    if got != h:
        print("MD5 NG", name); bad += 1
print("raw files checked:", len((RAW / "MD5.txt").read_text().splitlines()), "NG:", bad)
sys.exit(1 if bad else 0)

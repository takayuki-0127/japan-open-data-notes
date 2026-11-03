"""国税庁「法人番号公表サイト」全件データ（CSV・Unicode・全国、2026年10月30日更新、zip 約256MB）から、
集計に使う列だけを取り出し、月ごとの件数の表（法人名・法人番号・住所は持たない）を作る。

元データ: https://www.houjin-bangou.nta.go.jp/download/zenken/
ブラウザでダウンロードした 00_zenkoku_all_20261030.zip を --zip で指定して実行する。

列の位置（0始まり、ダウンロードファイルの仕様による）
 2 process（最新の処理区分）, 5 changeDate, 8 kind, 13 prefectureCode, 14 cityCode,
 18 closeDate, 19 closeCause, 22 assignmentDate

出力（data/raw/）
- cells_20261030.csv.gz : 1行＝（指定の時期, 法人種別, 地域, 閉鎖の年月, 閉鎖の事由）の件数
    group: old＝2015-11-01 より前に指定（制度開始時にあった法人）, new＝それ以後に指定（新しく設立された法人）
    assign_ym: new は指定の年月、old は空
- revival_20261030.csv.gz : 最新の処理区分が「登記記録の復活等」(22) の法人の、復活の年月ごとの件数
- alive_process_20261030.csv.gz : 登記が残っている法人の、最新の処理区分（01＝指定のあと変更なし、12＝所在地の変更、11＝商号の変更など）と最新の変更の年ごとの件数
"""
import argparse, csv, io, zipfile, collections, gzip
from common import RAW

def area_of(pref, city):
    try:
        p, c = int(pref), int(city)
    except ValueError:
        return "", ""
    if not 1 <= p <= 47:
        return "", ""
    a = "東京23区" if (p == 13 and 101 <= c <= 123) else ("政令市" if 100 <= c <= 199 else "その他の市町村")
    return str(p), a

def rows_from_zip(path):
    z = zipfile.ZipFile(path)
    name = [n for n in z.namelist() if n.endswith(".csv")][0]
    for r in csv.reader(io.TextIOWrapper(z.open(name), encoding="utf-8-sig")):
        yield r[2], r[5], r[8], r[13], r[14], r[18], r[19], r[22]

def build(rows):
    cells, rev, alive = collections.Counter(), collections.Counter(), collections.Counter()
    for process, change, kind, pref, city, close, cause, assign in rows:
        p, a = area_of(pref, city)
        if not p:
            continue
        old = assign < "2015-11-01"
        g = "old" if old else "new"
        cells[(g, "" if old else assign[:7], kind, p, a, close[:7], cause)] += 1
        if not close:
            alive[(g, kind, a, process, change[:4])] += 1
        if process == "22":
            rev[(g, kind, p, a, change[:7])] += 1
    RAW.mkdir(parents=True, exist_ok=True)
    with gzip.open(RAW / "cells_20261030.csv.gz", "wt", encoding="utf-8", newline="") as f:
        w = csv.writer(f); w.writerow(["group", "assign_ym", "kind", "pref", "area", "close_ym", "cause", "n"])
        for k, v in sorted(cells.items()): w.writerow([*k, v])
    with gzip.open(RAW / "revival_20261030.csv.gz", "wt", encoding="utf-8", newline="") as f:
        w = csv.writer(f); w.writerow(["group", "kind", "pref", "area", "revive_ym", "n"])
        for k, v in sorted(rev.items()): w.writerow([*k, v])
    with gzip.open(RAW / "alive_process_20261030.csv.gz", "wt", encoding="utf-8", newline="") as f:
        w = csv.writer(f); w.writerow(["group", "kind", "area", "process", "change_y", "n"])
        for k, v in sorted(alive.items()): w.writerow([*k, v])

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--zip", default="00_zenkoku_all_20261030.zip")
    build(rows_from_zip(ap.parse_args().zip)); print("done")

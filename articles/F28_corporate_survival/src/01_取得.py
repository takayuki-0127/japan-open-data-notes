"""国税庁 法人番号公表サイトの全件データ（CSV・Unicode、全国）から、分析に使う列だけを抜き出す。

元データ: https://www.houjin-bangou.nta.go.jp/download/zenken/ （2026年9月30日更新版、zip 約256MB・CSV 約1.27GB）
ブラウザでダウンロードした 00_zenkoku_all_YYYYMMDD.zip をこのスクリプトと同じ場所か --zip で指定して実行する。

出力（data/raw/）
- houjin_new_2015_2026.csv.gz : 2015-11-01 以降に法人番号が指定された法人（＝ほぼ設立登記された法人）1件1行。
  列: kind（法人種別）, pref, city（所在地の都道府県・市区町村コード）, assign（指定日）, close（登記記録の閉鎖日）, cause（閉鎖の事由）
  法人名・法人番号・住所は持たない。
- houjin_yearly_counts.csv : 全法人の年別の新規指定数と閉鎖数（事由・種別別）

列の位置は「法人番号公表サイト ダウンロードファイルの仕様」による（0始まり）:
 2 process, 8 kind, 13 prefectureCode, 14 cityCode, 18 closeDate, 19 closeCause, 22 assignmentDate, 23 latest
"""
import argparse, csv, gzip, io, zipfile, collections
from common import RAW

ap = argparse.ArgumentParser(); ap.add_argument("--zip", default="00_zenkoku_all_20260930.zip"); a = ap.parse_args()
z = zipfile.ZipFile(a.zip)
name = [n for n in z.namelist() if n.endswith(".csv")][0]
rd = csv.reader(io.TextIOWrapper(z.open(name), encoding="utf-8-sig"))
RAW.mkdir(parents=True, exist_ok=True)
cnt = collections.Counter()
with gzip.open(RAW / "houjin_new_2015_2026.csv.gz", "wt", encoding="utf-8", newline="") as g:
    w = csv.writer(g); w.writerow(["kind", "pref", "city", "assign", "close", "cause"])
    for r in rd:
        kind, pref, city, close, cause, assign, latest = r[8], r[13], r[14], r[18], r[19], r[22], r[23]
        if latest != "1":
            continue
        if assign > "2015-11-01":
            w.writerow([kind, pref, city, assign, close, cause]); cnt[("new", assign[:4], "", kind)] += 1
        if close:
            cnt[("close", close[:4], cause, kind)] += 1
        else:
            cnt[("alive", "", "", kind)] += 1
with open(RAW / "houjin_yearly_counts.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["type", "year", "cause", "kind", "n"])
    for k, v in sorted(cnt.items()):
        w.writerow([*k, v])
print("done")

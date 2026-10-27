"""データの入手先（ブラウザで取得したファイルを data/raw/ に置いている）

- lfs.xlsx : 総務省統計局「労働力調査」長期時系列表1 a-1（主要項目・全国・月別）。F12 で取得したものを再利用。
  https://www.stat.go.jp/data/roudou/longtime/03roudou.html
- official_lfs_gaps.csv : 同「標本抽出方法、結果の推定方法及び推定値の標本誤差」（https://www.stat.go.jp/data/roudou/pdf/10.pdf）
  の（参考１）「基準人口の切替え等による変動分（基本集計）」を書き写したもの（万人・ポイント）。
- wage.csv : 厚生労働省「毎月勤労統計調査」全国・調査産業計・5人以上の賃金指数と前年同月比（F12 で取得したものを再利用）。
- maikin_kyotsu_yoy.csv : 同「【参考資料】共通事業所による前年同月比」（各月の確報ページの kyo*.xlsx）を
  2019年8月・2020年8月・2022年8月・2024年8月・2026年8月分の5ファイルから読み、2018年1月〜2026年8月をつないだもの。
  同じ月が複数のファイルにあるときは新しいファイルの値を使った。
- mhlw_gap_2009_2012.csv : 厚生労働省「毎月勤労統計調査の抽出替えに伴うギャップについて」（https://www.mhlw.go.jp/content/10700000/001401792.pdf）
  の2009年1月・2012年1月の数値。

このスクリプトは、ファイルがそろっているかを確かめるだけ。
"""
import hashlib
from common import RAW

for f in sorted(RAW.iterdir()):
    h = hashlib.sha256(f.read_bytes()).hexdigest()[:16]
    print(f"{f.name:32s} {f.stat().st_size:>10,d} bytes  sha256:{h}")

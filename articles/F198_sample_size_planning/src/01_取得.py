"""01 取得：公表資料の数字を手で転記した（ダウンロードするファイルはない）。

転記元（2026年11月5日に閲覧）
- 総務省統計局「労働力調査 標本抽出方法、結果の推定方法及び推定値の標本誤差」
  https://www.stat.go.jp/data/roudou/pdf/10.pdf
  → data/lfs_se_by_size.csv（全国の推定値の大きさ別標準誤差、月次は2025年1〜12月の平均、年平均）
  → data/lfs_main_items_2025.csv（主要項目の年平均結果の標準誤差、2025年）
  → data/lfs_regional_se_annual.csv（地域別の年平均結果の標準誤差率）
- 各調査の「調査の概要」ページ → data/survey_designs.csv（標本の大きさ。ページの「約」の値のまま）
  労働力調査 https://www.stat.go.jp/data/roudou/outline.html
  家計調査   https://www.stat.go.jp/data/kakei/1.html
  社会生活基本調査（2021年） https://www.stat.go.jp/data/shakai/2021/gaiyou.html
  就業構造基本調査（2022年） https://www.stat.go.jp/data/shugyou/2022/gaiyou.html
  個人企業経済調査 https://www.stat.go.jp/data/kojinke/gaiyou_new.html
"""
from common import DATA

for f in sorted(DATA.glob("*.csv")):
    print(f.name, sum(1 for _ in open(f, encoding="utf-8")) - 1, "行")

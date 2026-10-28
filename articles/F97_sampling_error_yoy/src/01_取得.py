"""データの取得（記録）。
政府のサイトはこの作業環境から直接取れないため、ブラウザで取得したファイルを data/raw に置いた。
- 総務省統計局「家計調査年報（家計収支編）」各年の「家計調査の概要」PDF（2022〜2025年）
    https://www.stat.go.jp/data/kakei/{年}np/pdf/gaiyou.pdf  → data/raw/kakei_{年}_gaiyou.pdf
- 総務省統計局「家計調査」参考資料『変動係数を用いて推計した標準誤差率』（平成30年）
    https://www.stat.go.jp/data/kakei/pdf/30gai03.pdf → data/raw/kakei_2018_hyojungosa_sankou.pdf
- 総務省統計局「労働力調査」標本抽出方法、結果の推定方法及び推定値の標本誤差
    https://www.stat.go.jp/data/roudou/pdf/10.pdf → data/raw/roudou_hyohongosa.pdf
- 家計調査（家計収支編）二人以上の世帯 長期時系列表 品目分類 支出金額・名目増減率・実質増減率（月）
    e-Stat statInfId=000040270646・000040270647・000040270648（F11 で取得・整形したものを再利用）
- 労働力調査 完全失業率（季節調整値、月）1994年1月〜（F18 で取得したものを再利用）
"""
import shutil
from common import ROOT, RAW
A = ROOT.parent
shutil.copy(A/'F11_tax_hike_event/data/kakei_monthly_long.csv', RAW/'kakei_monthly_long_F11.csv')
shutil.copy(A/'F18_nowcast_dfm/data/monthly_levels.csv', RAW/'monthly_levels_F18.csv')
print('copied')

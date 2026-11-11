"""データの入手先（ブラウザで取得し data/raw/ に置いた）。このスクリプトはファイルの有無と大きさを確かめるだけ。

- maikin_jissu_cy2000.csv / maikin_shisu_cy2000.csv：厚生労働省「毎月勤労統計調査」全国調査 実数・指数累積データ
  （e-Stat statInfId=000032189776〔実数〕・000032189777〔指数・伸び率〕、CSV）から、年平均（月=CY）・2000年以降の行だけを取り出したもの。
  https://www.e-stat.go.jp/stat-search/files?page=1&toukei=00450071&tstat=000001011791
- chingin_hikiage_table1.csv / table4.csv：厚生労働省「賃金引上げ等の実態に関する調査」令和7年 時系列表 第1表・第4表
  （記事 141_wage_increase で整形したものを再利用）
- mw_national.csv：地域別最低賃金の全国加重平均（厚生労働省の公表値、各年度の改定後の額）を書き写したもの
"""
from common import RAW
for f in sorted(RAW.iterdir()):
    print(f"{f.name:34s} {f.stat().st_size:>10,d} bytes")

# SOURCES（元データの取得元）

取得日：2026-11-18（01_fetch.py で取得）

| ファイル | URL | sha256 の先頭12字 |
|---|---|---|
| an_jpn.csv | https://www.data.jma.go.jp/cpdinfo/temp/list/csv/an_jpn.csv | 2a93342ee904 |
| an_wld.csv | https://www.data.jma.go.jp/cpdinfo/temp/list/csv/an_wld.csv | 08deb89fbdb9 |
| ssn_jpn.csv | https://www.data.jma.go.jp/cpdinfo/temp/list/csv/ssn_jpn.csv | 1a374ba7e651 |
| ssn_wld.csv | https://www.data.jma.go.jp/cpdinfo/temp/list/csv/ssn_wld.csv | e0351bbf48e8 |
| sst_global.txt | https://ds.data.jma.go.jp/gmd/kaiyou/data/shindan/a_1/glb_warm/global.txt | 9d093ff789d7 |
| page_an_jpn.html | https://www.data.jma.go.jp/cpdinfo/temp/an_jpn.html | f29ba929d595 |
| page_an_wld.html | https://www.data.jma.go.jp/cpdinfo/temp/an_wld.html | 3c205fb2ca74 |
| page_land_an_wld.html | https://www.data.jma.go.jp/cpdinfo/temp/land/land_an_wld.html | a3c7bbb06410 |

CSV は Shift_JIS（cp932）。偏差の基準は1991〜2020年の平均。
page_*.html は、気象庁が公表している上昇率（100年あたり）を照合するために保存した解説ページ。
世界の陸上のみの年平均気温は、気象庁のページに図と上昇率の文章はあるが、数値の表（CSV）は見つからなかった。

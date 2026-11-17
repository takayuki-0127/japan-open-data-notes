# SOURCES（元データの取得元）

取得日：2026-11-16（src/01_fetch.py と同じ URL から取得）

| ファイル | 中身 | URL | sha256 の先頭12字 |
|---|---|---|---|
| timeseriesSCT_e.csv | 財務省「貿易取引通貨別比率」輸出 時系列（半期、2000年下半期〜2026年上半期） | https://www.customs.go.jp/toukei/shinbun/tuuka/timeseriesSCT_e.csv | 6d41ecb661ba |
| timeseriesSCT_i.csv | 同 輸入 | https://www.customs.go.jp/toukei/shinbun/tuuka/timeseriesSCT_i.csv | 5960cc689a23 |
| d51ma.csv | 財務省「貿易統計」輸出入額の推移 世界 月別（輸出）主要商品別（総額の列を使用） | https://www.customs.go.jp/toukei/suii/html/data/d51ma.csv | 88178276c664 |
| d52ma001.csv | 同 米国 月別（輸出） | https://www.customs.go.jp/toukei/suii/html/data/d52ma001.csv | 30fda593b0a6 |
| d52ma002.csv | 同 EU 月別（輸出） | https://www.customs.go.jp/toukei/suii/html/data/d52ma002.csv | 6731fcb703cf |
| d52ma003.csv | 同 アジア 月別（輸出） | https://www.customs.go.jp/toukei/suii/html/data/d52ma003.csv | 33b06b03a736 |
| boj_usdjpy_monthly.json | 日本銀行「外国為替相場」ドル・円 17時時点 月中平均（FM08 FXERM07）2000年1月〜2026年6月 | https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db=FM08&code=FXERM07&startDate=200001&endDate=202606 | 183e87ff522a |

- 財務省の CSV は Shift_JIS（cp932）。

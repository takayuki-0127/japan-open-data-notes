# SOURCES（元データの取得元）

取得日：2026-11-16（src/01_fetch.py と同じ URL から取得）

| ファイル | 中身 | URL | sha256 の先頭12字 |
|---|---|---|---|
| d61ca.csv | 財務省「貿易統計」輸出入額の推移 世界 年別（輸入）主要商品別 金額（千円）・数量（1988〜2025年） | https://www.customs.go.jp/toukei/suii/html/data/d61ca.csv | e167b67edf24 |
| boj_usdjpy_monthly.json | 日本銀行「外国為替相場」ドル・円 17時時点 月中平均（FM08 FXERM07）1988年1月〜2025年12月 | https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db=FM08&code=FXERM07&startDate=198801&endDate=202512 | d81dc2e1075a |
| boj_import_prices_monthly.json | 日本銀行「企業物価指数」輸入物価指数（2020年基準）飲食料品・食料用農水産物（円・契約通貨ベース）と総平均 | https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db=PR01&code=PRCG20_2600120001,PRCG20_2500120001,PRCG20_2600000000,PRCG20_2500000000&startDate=198801&endDate=202512 | 3cf6caab0177 |

- d61ca.csv は Shift_JIS（cp932）。品目コードの列が数量、その右の列が金額。

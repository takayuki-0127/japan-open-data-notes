# SOURCES（元データの取得元）

取得日：2026-11-16（01_fetch.py で取得）

| ファイル | 中身 | URL | sha256 の先頭12字 |
|---|---|---|---|
| customs_world_total_yearly.csv | 財務省 貿易統計 輸出入額の推移 世界 年別（総額、千円） | https://www.customs.go.jp/toukei/suii/html/data/d41ca.csv | 1df21a07a58d |
| customs_world_exports_by_commodity_yearly.csv | 同 世界 年別 輸出 主要商品別（金額・数量） | https://www.customs.go.jp/toukei/suii/html/data/d51ca.csv | 50a43b7de190 |
| customs_world_imports_by_commodity_yearly.csv | 同 世界 年別 輸入 主要商品別（金額・数量） | https://www.customs.go.jp/toukei/suii/html/data/d61ca.csv | e167b67edf24 |
| boj_usdjpy_monthly.json | 日本銀行 時系列統計データ FM08 FXERM07 ドル・円 東京市場 17時時点 月中平均 | https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db=FM08&code=FXERM07&startDate=198001&endDate=202512 | c93b844223e9 |
| boj_import_prices_monthly.json | 日本銀行 企業物価指数 PR01 輸入物価指数・輸出物価指数 総平均（円ベース・契約通貨ベース、2020年=100） | https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db=PR01&code=PRCG20_2600000000,PRCG20_2500000000,PRCG20_2400000000,PRCG20_2300000000&startDate=200001&endDate=202512 | e1b109db8ef4 |

出典：財務省「貿易統計」（税関ホームページ 輸出入額の推移）、日本銀行「時系列統計データ」。財務省の CSV は Shift_JIS（cp932）。

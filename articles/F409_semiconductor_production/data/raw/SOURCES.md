# SOURCES（元データの取得元）

取得日：2026-11-18（src/01_fetch.py で取得）

| ファイル | 中身 | URL | sha256 の先頭12字 | バイト数 |
|---|---|---|---|---|
| iip2020_gyoshu_sa.xlsx | 経済産業省「鉱工業指数」2020年基準 業種別 月次 季節調整済指数（生産・出荷・在庫・在庫率、2018年1月〜2026年9月） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040172363&fileKind=0 | 5c04e402354f | 367849 |
| iip2020_hinmoku_sa.xlsx | 経済産業省「鉱工業指数」2020年基準 品目別 月次 季節調整済指数（同） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040172367&fileKind=0 | 36932e49077c | 864867 |
| iip2015_gyoshu_sa.xlsx | 経済産業省「鉱工業指数」2015年基準 業種別 月次 季節調整済指数（2013年1月〜2023年4月） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000032122500&fileKind=0 | 51f329b8ec25 | 429016 |
| customs_export_monthly.csv | 財務省「貿易統計」輸出入額の推移 世界 月別 輸出 主要商品別（千円、1988年1月〜、Shift_JIS） | https://www.customs.go.jp/toukei/suii/html/data/d51ma.csv | 88178276c664 | 419344 |
| customs_import_monthly.csv | 財務省「貿易統計」輸出入額の推移 世界 月別 輸入 主要商品別（同） | https://www.customs.go.jp/toukei/suii/html/data/d61ma.csv | e072f1689fa7 | 426940 |
| boj_price_ic.csv | 日本銀行「企業物価指数」輸出・輸入物価指数の集積回路など9系列（時系列統計データ検索サイトの API、CSV、Shift_JIS） | https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=csv&lang=jp&db=PR01&startDate=201001&endDate=202610&code=PRCG15_2400540003,PRCG20_2400540002,PRCG15_2300540003,PRCG20_2300540002,PRCG15_2300550005,PRCG20_2300550006,PRCG15_2600840003,PRCG20_2600840002,PRCG20_2201550005 | 27e74d14804e | 232454 |

- e-Stat の鉱工業指数の一覧：https://www.e-stat.go.jp/stat-search/files?layout=dataset&toukei=00550300
- 財務省貿易統計 輸出入額の推移：https://www.customs.go.jp/toukei/suii/html/time.htm
- 日本銀行 時系列統計データ検索サイト：https://www.stat-search.boj.or.jp/
- 経済産業省のサイト（www.meti.go.jp/statistics/）は 403 を返したため、同じ指数を e-Stat の掲載分から取った（2026-11-18）。
- 世界の半導体の売上（WSTS）は、業界団体の資料で再配布の扱いがはっきりしないため使っていない。世界の値動きは、日銀の輸出物価（契約通貨ベース、ドル建てなどの値段）で見る。

出典：経済産業省「鉱工業指数」（e-Stat）、財務省「貿易統計」、日本銀行「企業物価指数」。

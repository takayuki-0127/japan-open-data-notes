# SOURCES（元データの取得元）

取得日：2026-11-16（src/01_fetch.py で取得）

| ファイル | 中身 | URL | sha256 の先頭12字 |
|---|---|---|---|
| deflator_fy2020base.xlsx | 建設工事費デフレーター（2020年度基準）時系列（年度別） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040459205&fileKind=0 | 42402896b01a |
| deflator_weights_2011base.xlsx | 建設工事費デフレーター（平成23年度基準）表-3 個別デフレーターウエイト表 | https://www.mlit.go.jp/common/001190414.xlsx | f5a63fad8cc4 |
| maikin_wage_index.xls | 毎月勤労統計調査 実数・指数累積データ 表7 現金給与総額 指数（5人以上、就業形態計、産業別シート） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000032189720&fileKind=4 | cb874a917da9 |
| maikin_hours_index.xls | 毎月勤労統計調査 実数・指数累積データ 表29 総実労働時間 指数（5人以上、就業形態計、産業別シート） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000032189742&fileKind=4 | 779b753b446f |
| boj_cgpi2020_monthly.json | 日本銀行 企業物価指数（2020年基準）国内企業物価指数 総平均と類別（木材・木製品、石油・石炭製品、プラスチック製品、窯業・土石製品、鉄鋼、非鉄金属、金属製品）月次 | https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db=PR01&startDate=198001&endDate=202612&code=PRCG20_2200000000,PRCG20_2200320001,PRCG20_2200620001,PRCG20_2200720001,PRCG20_2200820001,PRCG20_2200920001,PRCG20_2201020001,PRCG20_2201120001 | 0fa2a9756b27 |

出典：国土交通省「建設工事費デフレーター」、厚生労働省「毎月勤労統計調査」、日本銀行「企業物価指数」。

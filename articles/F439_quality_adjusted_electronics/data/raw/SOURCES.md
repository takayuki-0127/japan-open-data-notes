# SOURCES（元データの取得元）

取得日：2026-11-18（src/01_fetch.py と同じ URL から取得）

| ファイル | 中身 | URL | sha256 の先頭12字 |
|---|---|---|---|
| cpi2025_item_annual.csv | 消費者物価指数 2025年基準 全国 品目別価格指数（年平均＝暦年、1970年〜2025年） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040482831&fileKind=1 | cfa494f77d7b |
| cpi2025_item_monthly.csv | 消費者物価指数 2025年基準 全国 品目別価格指数（月次、1970年1月〜2026年9月） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040482945&fileKind=1 | 15c42c311c93 |
| cpi2020_item_annual.csv | 消費者物価指数 2020年基準 全国 品目別価格指数（年平均＝暦年、1970年〜2025年） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000032103938&fileKind=1 | 33fbf128935f |
| cpi2015_item_annual.csv | 消費者物価指数 2015年基準 全国 品目別価格指数（年平均＝暦年、1970年〜2021年） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031431772&fileKind=1 | 3bf13084b168 |
| trade_import_world_annual.csv | 財務省 貿易統計 輸出入額の推移 輸入 世界 年別 主要商品別（金額・数量） | https://www.customs.go.jp/toukei/suii/html/data/d61ca.csv | e167b67edf24 |

- 消費者物価指数の CSV は Shift_JIS（cp932）。1〜6行目が見出し（類・品目名、英語名、符号、連番、ウエイト、ウエイト1万分比）、7行目からが年（または年月）。
- 暦年の値は「年平均」の表（2025年基準は 000040482831）を使った。年度平均の表（000040482959）は使っていない。
- 貿易統計の CSV も Shift_JIS。金額は千円、数量の単位は列ごとに書かれている（電算機類・電話機は台＝NO）。
- e-Stat のデータ・貿易統計は、政府標準利用規約（第2.0版）に従い、出典を示して加工して使う。

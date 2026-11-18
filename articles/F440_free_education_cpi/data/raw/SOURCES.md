# SOURCES（元データの取得元）

取得日：2026-11-18（src/01_fetch.py と同じ URL から取得）

| ファイル | 中身 | URL | sha256 の先頭12字 |
|---|---|---|---|
| cpi2015_item_monthly.csv | 消費者物価指数 2015年基準 全国 品目別価格指数（月次、1970年1月〜2021年12月） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031431698&fileKind=1 | bd1f55cb0df2 |
| cpi2015_item_annual.csv | 消費者物価指数 2015年基準 全国 品目別価格指数（年平均＝暦年、1970年〜2021年） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031431772&fileKind=1 | 3bf13084b168 |
| cpi2020_item_monthly.csv | 消費者物価指数 2020年基準 全国 品目別価格指数（月次、1970年1月〜） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000032103844&fileKind=1 | e8f32d29cbdb |
| cpi2020_item_annual.csv | 消費者物価指数 2020年基準 全国 品目別価格指数（年平均＝暦年、1970年〜2025年） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000032103938&fileKind=1 | 33fbf128935f |
| cpi2025_item_monthly.csv | 消費者物価指数 2025年基準 全国 品目別価格指数（月次、1970年1月〜2026年9月） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040482945&fileKind=1 | 15c42c311c93 |
| cpi2025_item_annual.csv | 消費者物価指数 2025年基準 全国 品目別価格指数（年平均＝暦年、1970年〜2025年） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040482831&fileKind=1 | cfa494f77d7b |
| cpi2025_middle_annual.csv | 消費者物価指数 2025年基準 全国 中分類指数（年平均＝暦年、1970年〜2025年） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040482829&fileKind=1 | f639475ca393 |

- CSV は Shift_JIS（cp932）。1〜6行目が見出し（類・品目名、英語名、符号、連番、ウエイト、ウエイト1万分比）、7行目からが年（または年月）。
- 暦年の値は「年平均」の表を使った（2025年基準：品目別 000040482831・中分類 000040482829、2020年基準：000032103938、2015年基準：000031431772）。年度平均の表（000040482959・000040482957 など）は使っていない。
- e-Stat のデータは、政府標準利用規約（第2.0版）に従い、出典を示して加工して使う。
- 2015年基準の月次は全国の表（000031431698）を使った。はじめ 000031431788 を取ったが、総合のウエイト（256,632,267）が全国の年平均の表（3,139,338,474）と合わず、年平均も全国の値と一致しなかったため、全国の表ではない（推測：東京都区部の表）と判断して取り替えた。

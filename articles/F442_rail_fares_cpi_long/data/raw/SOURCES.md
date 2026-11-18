# 元データの出典（取得日と URL）

取得日：2026-11-18（src/01_fetch.py で取得）

| ファイル | 中身 | URL | sha256 の先頭12字 |
|---|---|---|---|
| cpi2025_item_monthly.csv | 総務省「消費者物価指数」2025年基準 全国 品目別価格指数（月次、1970年1月〜2026年9月）。e-Stat statInfId 000040482945 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040482945&fileKind=1 | 15c42c311c93 |
| cpi2025_goods_services_monthly.csv | 同 財・サービス分類指数（月次）。000040482946 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040482946&fileKind=1 | 9dbdf0785afc |
| cpi2025_item_annual_cy.csv | 同 品目別価格指数 **年平均（暦年）**（1970〜2025年）。000040482831 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040482831&fileKind=1 | cfa494f77d7b |
| cpi2025_goods_services_annual_cy.csv | 同 財・サービス分類指数 **年平均（暦年）**。000040482832 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040482832&fileKind=1 | ca91bda72947 |

- どの CSV も Shift_JIS（cp932）。指数は2025年＝100、消費税を含む値段。
- 年の値は暦年の表を使った。年度平均の表（品目別 000040482959、中分類 000040482957 など）は使っていない。
- 統計表一覧：https://www.e-stat.go.jp/stat-search/files?toukei=00200573&tstat=000001243876
- 出典：総務省統計局「消費者物価指数」（政府統計の総合窓口 e-Stat）。

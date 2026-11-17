# SOURCES（元データの取得元）

取得日：2026-11-16（src/01_fetch.py と同じ URL から取得）

| ファイル | 中身 | URL | sha256 の先頭12字 |
|---|---|---|---|
| cpi_item_monthly.csv | 総務省「消費者物価指数」2025年基準 全国 品目別価格指数（月次、1970年1月〜2026年9月、Shift_JIS） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040482945&fileKind=1 | 15c42c311c93 |
| boj_usdjpy_monthly.json | 日本銀行「外国為替相場」ドル・円 17時時点 月中平均（FM08 FXERM07）2000年1月〜2026年9月 | https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db=FM08&code=FXERM07&startDate=200001&endDate=202609 | 5c3ddf2cd61d |

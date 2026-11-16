# SOURCES（元データの取得元）

取得日：2026-11-16（src/01_fetch.py と同じ URL から取得）

| ファイル | 中身 | URL | sha256 の先頭12字 |
|---|---|---|---|
| cpi_zenkoku_item_monthly.csv | 総務省「消費者物価指数」2025年基準 全国 品目別価格指数（月次、1970年1月〜2026年9月、Shift_JIS） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040482945&fileKind=1 | 15c42c311c93 |
| cpi_kubu_item_monthly.csv | 同 東京都区部 品目別価格指数（月次、1970年1月〜2026年10月、Shift_JIS） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040482967&fileKind=1 | a83569b15bf0 |
| jnto_visitors_2003_2026.xlsx | 日本政府観光局（JNTO）「国籍/月別 訪日外客数（2003年～2026年）」（2026年10月21日掲載版） | https://www.jnto.go.jp/statistics/data/_files/20261021_1615-5.xlsx | e6cd0aadd774 |

- 使った列：宿泊料（類・品目符号 0139）、総合（0001）。訪日外客数は各年のシートの「総数」の行。
- 訪日外客数の最近の月は推計値・暫定値を含む。
- 政府統計の総合窓口（e-Stat）と JNTO のサイトから取得。出典を示して加工して使う。

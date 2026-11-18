# SOURCES（元データの取得元）

取得日：2026-11-18（src/01_fetch.py で取得）

| ファイル | 中身 | URL | sha256 の先頭12字 |
|---|---|---|---|
| chakko_yoto_pref_fy_000040451302.xls | 建築着工統計調査 建築物着工統計 時系列表【建築物】構造別 用途別 都道府県別（年度、1988〜2025年度、シートは年度ごと） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040451302&fileKind=0 | 9f7cbd1fe3ef |

- ファイル一覧：https://www.e-stat.go.jp/stat-search/files?toukei=00600120&tstat=000001016965（時系列表・年度次）
- 令和6年度は「4月〜12月」「1月〜3月」の2シートに分かれている（02_build.py で足す）。
- e-Stat のファイルは政府標準利用規約（第2.0版）に従い、出典を示して加工して使う。

出典：国土交通省「建築着工統計調査」。

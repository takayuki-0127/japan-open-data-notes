# SOURCES（元データの取得元）

取得日：2026-11-16（01_fetch.py で取得）

| ファイル | 中身 | URL | sha256 の先頭12字 |
|---|---|---|---|
| download/municipal_keinen.xlsx | 公共施設状況調経年比較表 市町村経年比較表（平成18年度〜令和6年度）。同梱せず、01b_extract.py で抜き出す | https://www.soumu.go.jp/main_content/001068878.xlsx | fe1cb8df84d1 |
| raw/jukijin_2025_municipal.xlsx | 住民基本台帳 2025年1月1日 【総計】市区町村別人口 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040306653&fileKind=0 | 5e6c474d2b0c |
| raw/jukijin_2020_municipal.xls | 住民基本台帳 2020年1月1日 【総計】市区町村別人口 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031971203&fileKind=0 | 65da53be4fde |
| raw/sewage_extract.csv | 上の市町村経年比較表から src/01b_extract.py で「下水道等」の列だけを抜き出したもの（同梱） | — | — |

- 公共施設状況調経年比較表：https://www.soumu.go.jp/iken/shisetsu/index.html
- 国の発表（令和6年度末の汚水処理人口普及状況）：https://www.mlit.go.jp/report/press/mizukokudo13_hh_000669.html

出典：総務省「公共施設状況調経年比較表」「住民基本台帳に基づく人口、人口動態及び世帯数調査」。

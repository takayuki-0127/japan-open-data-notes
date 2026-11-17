# SOURCES（元データの取得元）

取得日：2026-11-16（01_fetch.py で取得）

| ファイル | 中身 | URL | sha256 の先頭12字 |
|---|---|---|---|
| download/municipal_keinen.xlsx | 公共施設状況調経年比較表 市町村経年比較表（平成18年度〜令和6年度）。同梱せず、01b_extract.py で抜き出す | https://www.soumu.go.jp/main_content/001068878.xlsx | fe1cb8df84d1 |
| raw/pop_pref_2000_2020.xlsx | 人口推計 長期時系列 第5表 都道府県別人口（各年10月1日現在、2000〜2020年） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000013168605&fileKind=4 | 9e28da4c0ef8 |
| raw/pop_pref_2020_2024.xlsx | 人口推計 2024年 第5表 都道府県、男女別人口（各年10月1日現在） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040268859&fileKind=0 | aec6333067aa |
| raw/municipal_extract.csv | 上の市町村経年比較表から、src/01b_extract.py で使う列だけを抜き出したもの（同梱） | — | — |

- 公共施設状況調経年比較表：https://www.soumu.go.jp/iken/shisetsu/index.html
- 人口推計：https://www.e-stat.go.jp/stat-search/files?toukei=00200524&tstat=000000090001

出典：総務省「公共施設状況調経年比較表」「人口推計」。

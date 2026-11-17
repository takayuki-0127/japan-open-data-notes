# SOURCES（元データの取得元）

取得日：2026-11-17（src/01_fetch.py で取得）

| ファイル | 中身 | URL | sha256 の先頭12字 |
|---|---|---|---|
| meti_cvs_timeseries.xlsx | 経済産業省「商業動態統計」時系列データ コンビニエンスストア商品別販売額等及び前年（度、同期、同月）比（月次・四半期・年、全国・経済産業局別、1997年〜） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031387995&fileKind=0 | 73c92c1e6eb7 |
| cpi_item_annual.csv | 総務省「消費者物価指数」2025年基準 全国 品目別価格指数。**年度平均**の表（2025年の総合が100.4）で、暦年の年平均ではなかったため、レビュー（2026-11-18）以降は使っていない（記録として残す） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040482959&fileKind=1 | 7ce020001725 |
| cpi_annual_middle_class.csv | 総務省「消費者物価指数」2025年基準 全国 中分類指数（暦年の年平均、1970〜2025年、CSV、Shift_JIS）。2026-11-18 のレビューで取得して追加し、物価はこの表を使う | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040482829&fileKind=1 | f639475ca393 |
| pop_pref_2000_2020.xlsx | 総務省「人口推計」長期時系列 第5表 都道府県別人口（各年10月1日現在、2000〜2020年） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000013168605&fileKind=4 | 9e28da4c0ef8 |
| pop_pref_2020_2024.xlsx | 総務省「人口推計」2024年 第5表 都道府県、男女別人口（各年10月1日現在、2020〜2024年） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040268859&fileKind=0 | aec6333067aa |

出典：経済産業省「商業動態統計」、総務省「消費者物価指数」「人口推計」（いずれも政府統計の総合窓口 e-Stat）。

- 注：消費者物価指数の statInfId=000040482959（品目別）・000040482957（中分類）は年度平均の表。暦年の年平均は 000040482829（中分類）を使う。

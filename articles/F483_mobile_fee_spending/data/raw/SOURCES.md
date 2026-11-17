# SOURCES（元データの取得元）

取得日：2026-11-16（01_fetch.py で取得）

| ファイル | 中身 | URL | sha256 の先頭12字 |
|---|---|---|---|
| kakei_two_plus_items_nominal_2000_2025.csv | 家計調査 長期時系列 表1-2 二人以上の世帯 品目分類 支出金額（年、2000年〜） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040270652&fileKind=1 | f292df314949 |
| kakei_single_items_2000_2025.csv | 家計調査 長期時系列 表6 単身世帯 品目分類 支出金額（年、2000年〜） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040270666&fileKind=1 | 78269524b142 |
| cpi_item_annual.csv | 消費者物価指数 2025年基準 全国 品目別価格指数（暦年の年平均） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040482831&fileKind=1 | cfa494f77d7b |
| kakei_4-6_2015.xls | 家計調査 2015年 二人以上の世帯 第4-6表 世帯主の年齢階級別（品目分類） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031370144&fileKind=0 | 7d1e6780a04f |
| kakei_4-6_2016.xls | 家計調査 2016年 二人以上の世帯 第4-6表 世帯主の年齢階級別（品目分類） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031534707&fileKind=0 | 92624f891e36 |
| kakei_4-6_2017.xls | 家計調査 2017年 二人以上の世帯 第4-6表 世帯主の年齢階級別（品目分類） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031674349&fileKind=0 | d810f121c458 |
| kakei_4-6_2018.xls | 家計調査 2018年 二人以上の世帯 第4-6表 世帯主の年齢階級別（品目分類） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031795471&fileKind=0 | 38b487d199de |
| kakei_4-6_2019.xls | 家計調査 2019年 二人以上の世帯 第4-6表 世帯主の年齢階級別（品目分類） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031909558&fileKind=0 | 65fe6b45bde2 |
| kakei_4-6_2020.xlsx | 家計調査 2020年 二人以上の世帯 第4-6表 世帯主の年齢階級別（品目分類） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000032048838&fileKind=0 | 1094b21d997c |
| kakei_4-6_2021.xlsx | 家計調査 2021年 二人以上の世帯 第4-6表 世帯主の年齢階級別（品目分類） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000032167634&fileKind=0 | ec07a1a82c05 |
| kakei_4-6_2022.xlsx | 家計調査 2022年 二人以上の世帯 第4-6表 世帯主の年齢階級別（品目分類） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040015264&fileKind=0 | ed81aa9b590b |
| kakei_4-6_2023.xlsx | 家計調査 2023年 二人以上の世帯 第4-6表 世帯主の年齢階級別（品目分類） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040140561&fileKind=0 | 5400d78d5955 |
| kakei_4-6_2024.xlsx | 家計調査 2024年 二人以上の世帯 第4-6表 世帯主の年齢階級別（品目分類） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040247212&fileKind=0 | 96410a073d59 |
| kakei_4-6_2025.xlsx | 家計調査 2025年 二人以上の世帯 第4-6表 世帯主の年齢階級別（品目分類） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040409549&fileKind=0 | b9e804f1dc44 |

出典：総務省統計局「家計調査（家計収支編）」「消費者物価指数」（e-Stat https://www.e-stat.go.jp/）。CSV は Shift_JIS（cp932）。

- 注（2026-11-18 訂正）：cpi_item_annual.csv は、はじめ statInfId=000040482959（品目別価格指数の**年度平均**の表。2025年の総合が100.4）を使っていた。暦年の統計と並べるため、暦年の年平均の表（statInfId=000040482831、2025年の総合が100.0）に取り直した（同じ行・列の並び）。

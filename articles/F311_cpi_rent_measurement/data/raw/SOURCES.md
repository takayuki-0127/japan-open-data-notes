# 元データの出典（取得日と URL）

| ファイル | 中身 | URL | 取得日 |
|---|---|---|---|
| cpi_item_annual.csv | 総務省「消費者物価指数」2025年基準 全国 品目別価格指数（暦年の年平均、1970年〜最新年、CSV） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040482831&fileKind=1 | 2026-11-18 |
| jutaku2023_t34_1_rent_timeseries.xlsx | 総務省「令和5年住宅・土地統計調査」時系列統計表 第34-1表 住宅の所有の関係別 1か月当たり家賃及び1畳当たり家賃―全国（1973〜2023年） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040354072&fileKind=4 | 2026-11-16 |
| jutaku2023_t27_rent_by_movein_construction.xlsx | 総務省「令和5年住宅・土地統計調査」第27表 入居時期・建築の時期別 借家数、1畳当たり家賃―全国 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040353891&fileKind=4 | 2026-11-16 |

- 消費者物価指数の時系列：https://www.e-stat.go.jp/stat-search/files?tstat=000001243876
- 令和5年住宅・土地統計調査：https://www.e-stat.go.jp/stat-search/files?toukei=00200522&tstat=000001207800
- 政府統計の総合窓口（e-Stat）から取得。政府標準利用規約（第2.0版）に従い、出典を示して加工して使う。

- 注（2026-11-18 訂正）：cpi_item_annual.csv は、はじめ statInfId=000040482959（品目別価格指数の**年度平均**の表。2025年の総合が100.4）を使っていた。暦年の統計と並べるため、暦年の年平均の表（statInfId=000040482831、2025年の総合が100.0）に取り直した（同じ行・列の並び）。

# 元データの出典（取得日と URL）

取得日：2026-11-16（01_fetch.py で取得）

| ファイル | 中身 | URL | sha256 の先頭12字 |
|---|---|---|---|
| t1_5_15_2021.xlsx | 2021年調査 表1-5-15 代表輸送機関別流動量・流動ロットの推移（2005〜2021年） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040041013&fileKind=0 | 23be39be3bfa |
| t1_5_15_2015.xls | 2015年調査 表1-5-15 代表輸送機関別流動量・流動ロットの推移（2000〜2015年） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031596952&fileKind=0 | 35052c8098d2 |
| t1_5_12_2021.xlsx | 2021年調査 表1-5-12 発産業業種別流動量・流動ロットの推移（2005〜2021年） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040041010&fileKind=0 | 687d1c66dfc4 |
| t2_7_1_2021.xlsx | 2021年調査 表2-7-1 発産業業種・流動ロット階層別流動量（代表輸送機関別）－重量－ | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040041123&fileKind=0 | 2e588ce4c3be |
| t2_7_2_2021.xlsx | 2021年調査 表2-7-2 発産業業種・流動ロット階層別流動量（代表輸送機関別）－件数－ | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040041124&fileKind=0 | 45c8a85e0251 |
| t2_7_1_2015.xls | 2015年調査 表2-7-1 発産業業種・流動ロット階層別流動量（代表輸送機関別）－重量－ | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031597002&fileKind=0 | 45aecd97d053 |
| t2_7_2_2015.xls | 2015年調査 表2-7-2 発産業業種・流動ロット階層別流動量（代表輸送機関別）－件数－ | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031597003&fileKind=0 | 6a14827f8b20 |

- 統計表の一覧：https://www.e-stat.go.jp/stat-search/files?toukei=00600620&tstat=000001103136
- 出典：国土交通省「全国貨物純流動調査（物流センサス）」（政府統計の総合窓口 e-Stat）。政府標準利用規約（第2.0版）に従い、出典を示して加工して使う。
- 流動量は「3日間調査」（調査した3日間の出荷）の拡大推計。流動ロット = 重量 ÷ 件数（トン／件）。

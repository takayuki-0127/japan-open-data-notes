# 元データの出典（取得日と URL）

取得日：2026-11-16（01_fetch.py で取得）

| ファイル | 中身 | URL | sha256 の先頭12字 |
|---|---|---|---|
| inbound_2014.xls.gz | 2014年 暦年 集計表（一般客） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031366561&fileKind=0 | 564f6a67d36d |
| inbound_2015.xls.gz | 2015年 暦年 集計表（一般客） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031509470&fileKind=0 | 089250108591 |
| inbound_2016.xls.gz | 2016年 暦年 集計表（一般客） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031562371&fileKind=0 | 9b41ab39d169 |
| inbound_2017.xls.gz | 2017年 暦年 集計表（一般客） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031958631&fileKind=0 | c3dae5c1d7db |
| inbound_2018.xls.gz | 2018年 暦年 集計表（一般客） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031958632&fileKind=0 | 41367e047917 |
| inbound_2019.xls.gz | 2019年 暦年 集計表（一般客） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031958633&fileKind=0 | 727126bdd601 |
| inbound_2023.xls.gz | 2023年 暦年 集計表（一般客） | https://www.mlit.go.jp/kankocho/content/002020300.xls | f2b70436322c |
| inbound_2024.xls.gz | 2024年 暦年 集計表（一般客） | https://www.mlit.go.jp/kankocho/content/002022649.xls | 678aa74cd3c0 |
| inbound_2025.xls.gz | 2025年 暦年 集計表（一般客） | https://www.mlit.go.jp/kankocho/content/002025515.xls | c5451c6d5f88 |

- 2014〜2019年：政府統計の総合窓口 e-Stat「訪日外国人消費動向調査（年確定値）」https://www.e-stat.go.jp/stat-search/files?toukei=00601030&tstat=000001079655
- 2023〜2025年：観光庁「インバウンド消費動向調査」https://www.mlit.go.jp/kankocho/tokei_hakusyo/gaikokujinshohidoko.html
- .xls.gz は取得した .xls をそのまま gzip で圧縮したもの。出典を示して加工して使う。

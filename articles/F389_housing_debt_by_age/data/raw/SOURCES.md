# SOURCES（元データの取得元）

取得日：2026-11-16（src/01_fetch.py で取得）

総務省「家計調査（貯蓄・負債編）」詳細結果表 二人以上の世帯（e-Stat）。第8-5表は全世帯、第8-24表は負債保有世帯。

| ファイル | 年 | 表 | URL | sha256 の先頭12字 |
|---|---|---|---|---|
| sav_2008_t8_5.xls | 2008 | 第8-5表 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000002932542&fileKind=0 | ee072b0f6b1f |
| sav_2008_t8_24.xls | 2008 | 第8-24表 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000002932555&fileKind=0 | 15557297c8e8 |
| sav_2009_t8_5.xls | 2009 | 第8-5表 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000007587485&fileKind=0 | 5ecc9c60768e |
| sav_2009_t8_24.xls | 2009 | 第8-24表 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000007587498&fileKind=0 | 77b25ee19bd1 |
| sav_2010_t8_5.xls | 2010 | 第8-5表 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000009487490&fileKind=0 | 61bfc01de798 |
| sav_2010_t8_24.xls | 2010 | 第8-24表 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000009487503&fileKind=0 | 416d956c173e |
| sav_2011_t8_5.xls | 2011 | 第8-5表 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000013074255&fileKind=0 | 44ebd22e9912 |
| sav_2011_t8_24.xls | 2011 | 第8-24表 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000013074268&fileKind=0 | 94423f42f60f |
| sav_2012_t8_5.xls | 2012 | 第8-5表 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000020728198&fileKind=0 | 26888743715f |
| sav_2012_t8_24.xls | 2012 | 第8-24表 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000020728211&fileKind=0 | b9055e31df29 |
| sav_2013_t8_5.xls | 2013 | 第8-5表 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000024924704&fileKind=0 | adf39a100782 |
| sav_2013_t8_24.xls | 2013 | 第8-24表 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000024924717&fileKind=0 | fbdeb8c628d0 |
| sav_2014_t8_5.xls | 2014 | 第8-5表 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000029729288&fileKind=0 | 471dedb5d86f |
| sav_2014_t8_24.xls | 2014 | 第8-24表 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000029729301&fileKind=0 | 68e1b9cf2896 |
| sav_2015_t8_5.xls | 2015 | 第8-5表 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031409652&fileKind=0 | dcd75da8c9f7 |
| sav_2015_t8_24.xls | 2015 | 第8-24表 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031409665&fileKind=0 | d54384576f8a |
| sav_2016_t8_5.xls | 2016 | 第8-5表 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031576978&fileKind=0 | 6e3cd0ea267b |
| sav_2016_t8_24.xls | 2016 | 第8-24表 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031576991&fileKind=0 | 8a4720390eb7 |
| sav_2017_t8_5.xls | 2017 | 第8-5表 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031697789&fileKind=0 | c2c646c16766 |
| sav_2017_t8_24.xls | 2017 | 第8-24表 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031697802&fileKind=0 | 0b64e40b5ced |
| sav_2018_t8_5.xls | 2018 | 第8-5表 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031821255&fileKind=0 | dd7ab030961c |
| sav_2018_t8_24.xls | 2018 | 第8-24表 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031821268&fileKind=0 | 72ce866995e8 |
| sav_2019_t8_5.xls | 2019 | 第8-5表 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031946728&fileKind=0 | de608dc1eed6 |
| sav_2019_t8_24.xls | 2019 | 第8-24表 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031946741&fileKind=0 | f6cca83e7b1e |
| sav_2020_t8_5.xlsx | 2020 | 第8-5表 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000032087777&fileKind=0 | ab4b7d7165ae |
| sav_2020_t8_24.xlsx | 2020 | 第8-24表 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000032087790&fileKind=0 | 32de506bee82 |
| sav_2021_t8_5.xlsx | 2021 | 第8-5表 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000032191002&fileKind=0 | bd41df9679e3 |
| sav_2021_t8_24.xlsx | 2021 | 第8-24表 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000032191015&fileKind=0 | 01357ca04e81 |
| sav_2022_t8_5.xlsx | 2022 | 第8-5表 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040053957&fileKind=0 | 5e7891f523b1 |
| sav_2022_t8_24.xlsx | 2022 | 第8-24表 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040053990&fileKind=0 | be7b38118f3f |
| sav_2023_t8_5.xlsx | 2023 | 第8-5表 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040180979&fileKind=0 | fd7ea0e557c3 |
| sav_2023_t8_24.xlsx | 2023 | 第8-24表 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040180992&fileKind=0 | 59e7634119ca |
| sav_2024_t8_5.xlsx | 2024 | 第8-5表 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040277213&fileKind=0 | d31273ffe349 |
| sav_2024_t8_24.xlsx | 2024 | 第8-24表 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040277226&fileKind=0 | 8c92c8e246f2 |
| sav_2025_t8_5.xlsx | 2025 | 第8-5表 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040456242&fileKind=0 | 7872052e05e1 |
| sav_2025_t8_24.xlsx | 2025 | 第8-24表 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040456255&fileKind=0 | 0205fc9e9d12 |

出典：総務省統計局「家計調査（貯蓄・負債編）」。

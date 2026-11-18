# SOURCES（元データの取得元）

取得日：2026-11-18（01_fetch.py で取得）

| ファイル | 中身 | URL | sha256 の先頭12字 |
|---|---|---|---|
| ts2_energy_by_attr_2017_2023.xlsx | 時系列第2表 基本項目別 年間エネルギー種別エネルギー消費量（2017〜2023年度） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031913551&fileKind=4 | b72c92f7242d |
| r7_sokuhou_fig1_3.xlsx | 令和7年度速報 図1-3・表1 世帯当たり年間エネルギー種別消費量の推移（全国） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040519206&fileKind=4 | 67b867eeac07 |
| t6_2_2_2017.xlsx | 2017年度 全国 第6-2-2表 機器・照明の使用台数、使用状況、製造時期、種類、大きさ別 年間エネルギー種別エネルギー消費量 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031788042&fileKind=0 | af3144f506c3 |
| t7_1_1_2017.xlsx | 2017年度 全国 第7-1-1表（参考）基本項目別 年間用途別エネルギー消費量 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031788069&fileKind=0 | 83ad802bdf24 |
| t6_2_2_2018.xlsx | 2018年度 全国 第6-2-2表 機器・照明の使用台数、使用状況、製造時期、種類、大きさ別 年間エネルギー種別エネルギー消費量 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031912836&fileKind=0 | 52fb203fe66b |
| t7_1_1_2018.xlsx | 2018年度 全国 第7-1-1表（参考）基本項目別 年間用途別エネルギー消費量 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031912863&fileKind=0 | 8bb242d63301 |
| t6_2_2_2019.xlsx | 2019年度 全国 第6-2-2表 機器・照明の使用台数、使用状況、製造時期、種類、大きさ別 年間エネルギー種別エネルギー消費量 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000032051954&fileKind=4 | 353357bb630d |
| t7_1_1_2019.xlsx | 2019年度 全国 第7-1-1表（参考）基本項目別 年間用途別エネルギー消費量 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000032051981&fileKind=4 | 187ba10cf3de |
| t6_2_2_2020.xlsx | 2020年度 全国 第6-2-2表 機器・照明の使用台数、使用状況、製造時期、種類、大きさ別 年間エネルギー種別エネルギー消費量 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000032171000&fileKind=4 | 83ba64187061 |
| t7_1_1_2020.xlsx | 2020年度 全国 第7-1-1表（参考）基本項目別 年間用途別エネルギー消費量 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000032171027&fileKind=4 | 182c3583bf63 |
| t6_2_2_2021.xlsx | 2021年度 全国 第6-2-2表 機器・照明の使用台数、使用状況、製造時期、種類、大きさ別 年間エネルギー種別エネルギー消費量 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040033346&fileKind=4 | 476a1830adaa |
| t7_1_1_2021.xlsx | 2021年度 全国 第7-1-1表（参考）基本項目別 年間用途別エネルギー消費量 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040033373&fileKind=4 | 1d0b8773bf26 |
| t6_2_2_2022.xlsx | 2022年度 全国 第6-2-2表 機器・照明の使用台数、使用状況、製造時期、種類、大きさ別 年間エネルギー種別エネルギー消費量 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040161446&fileKind=4 | 86d83cdf9d50 |
| t7_1_1_2022.xlsx | 2022年度 全国 第7-1-1表（参考）基本項目別 年間用途別エネルギー消費量 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040161473&fileKind=4 | a04c9e6edb9c |
| t6_2_2_2023.xlsx | 2023年度 全国 第6-2-2表 機器・照明の使用台数、使用状況、製造時期、種類、大きさ別 年間エネルギー種別エネルギー消費量 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040277733&fileKind=4 | 02fc6df25835 |
| t7_1_1_2023.xlsx | 2023年度 全国 第7-1-1表（参考）基本項目別 年間用途別エネルギー消費量 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040277760&fileKind=4 | 8e8abedaea45 |

- 調査の e-Stat ページ：https://www.e-stat.go.jp/stat-search/files?page=1&toukei=00650408
- 環境省の調査のページ：https://www.env.go.jp/earth/ondanka/ghg/kateiCO2tokei.html
- 値は年度（4月〜翌3月）。2024年度は調査がなく、2025年度は速報値。各年度の表の1〜3行目（年度・表題・「全国」）を 02_build.py で確かめる。

出典：環境省「家庭部門のCO2排出実態統計調査」。

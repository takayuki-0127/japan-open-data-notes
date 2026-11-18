# SOURCES（元データの取得元）

取得日：2026-11-18（src/01_fetch.py で取得）

| ファイル | 中身 | URL | sha256 の先頭12字 | バイト数 |
|---|---|---|---|---|
| nenpo2012_paper.xls | 経済産業省「生産動態統計」2012年 年報 紙・パルプ統計（製品時系列表：2008〜2012年の年計と月次、段ボールの消費部門別内訳） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000022159811&fileKind=0 | da6d49930a79 | 522240 |
| nenpo2017_paper.xls | 経済産業省「生産動態統計」2017年 年報 紙・パルプ統計（製品時系列表：2013〜2017年） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031703020&fileKind=0 | ff4bb8e8b8f7 | 561664 |
| nenpo2020_paper.xls | 経済産業省「生産動態統計」2020年 年報 紙・印刷・プラスチック・ゴム製品統計編（製品時系列表：2016〜2020年） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031961792&fileKind=0 | a76808e8e75f | 1019392 |
| nenpo2021.xlsx | 経済産業省「生産動態統計」2021年 年報（全品目の月次の実数表） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000032213834&fileKind=0 | 072d896073ca | 3157559 |
| nenpo2022.xlsx | 経済産業省「生産動態統計」2022年 年報（同） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040077080&fileKind=0 | 094ce5a6ee1a | 3099985 |
| nenpo2023.xlsx | 経済産業省「生産動態統計」2023年 年報（同） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040191921&fileKind=0 | 4959c0094cd2 | 3187354 |
| nenpo2024.xlsx | 経済産業省「生産動態統計」2024年 年報（同） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040293825&fileKind=0 | 14307dab7b1c | 2592344 |
| nenpo2025.xlsx | 経済産業省「生産動態統計」2025年 年報（同） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040475159&fileKind=0 | b07a16cdf7b3 | 2260480 |

- e-Stat の一覧：https://www.e-stat.go.jp/stat-search/files?toukei=00550200&tstat=000001022932
- 経済産業省のサイト（www.meti.go.jp/statistics/tyo/seidou/）は 2026-11-18 に 403 を返したため、同じ年報を e-Stat から取った。
- 2020年以前は分野別の年報（紙・パルプ統計）、2021年以降は全品目をまとめた年報（実数表、月次）。

出典：経済産業省「生産動態統計」。

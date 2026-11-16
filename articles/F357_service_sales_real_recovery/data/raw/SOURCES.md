# SOURCES（元データの取得元）

取得日：2026-11-16（src/01_fetch.py で取得）。この表は独立レビューで、01_fetch.py の取得先と同梱ファイルから書き起こしました。

| ファイル | 中身 | URL | sha256 の先頭12字 |
|---|---|---|---|
| mbss_ts_t1_aj10.xlsx | 総務省「サービス産業動態統計調査」時系列 第1表 事業活動の産業（中分類）別売上（収入）金額（月次） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040518944&fileKind=4 | f68d21f278f6 |
| mssi_annual_t3_2018_a030.xls | 総務省「サービス産業動向調査」2018年 年報 第3表 事業従事者規模別売上高 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031870669&fileKind=0 | b39d2df41340 |
| mssi_annual_t3_2019_a030.xls | 同 2019年 年報 第3表 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000032013135&fileKind=0 | c273973eaf40 |
| mssi_annual_t3_2023_a030.xls | 同 2023年 年報 第3表 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040215345&fileKind=4 | 03b4e9955653 |
| cpi2025_monthly_chubunrui_zmi2025s.csv | 総務省「消費者物価指数（2025年基準）」長期時系列 中分類指数（全国、月次） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040482943&fileKind=1 | 29b63b7aa5cb |
| cpi2025_monthly_zaisa_zmi2025b.csv | 同 財・サービス分類指数（全国、月次） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040482946&fileKind=1 | 9dbdf0785afc |
| cpi2025_monthly_hinmoku_zmi2025a.csv | 同 品目別価格指数（全国、月次） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040482945&fileKind=1 | 15c42c311c93 |
| boj_sppi2020_monthly.json | 日本銀行「企業向けサービス価格指数（2020年基準）」基本分類指数・類別・大類別（2013年1月〜、月次。系列コードは src/01_fetch.py の SPPI_CODES） | https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db=PR02&startDate=201301&endDate=202612&code=（PRCS20_ で始まる系列コード、src/01_fetch.py を参照） | 90da80962a37 |

出典：総務省「サービス産業動態統計調査」「サービス産業動向調査」「消費者物価指数」、日本銀行「企業向けサービス価格指数」。

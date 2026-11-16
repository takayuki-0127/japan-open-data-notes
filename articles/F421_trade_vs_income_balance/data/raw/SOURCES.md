# SOURCES（元データの取得元）

取得日：2026-11-16（src/01_fetch.py と同じ URL から取得）

| ファイル | 中身 | URL | sha256 の先頭12字 |
|---|---|---|---|
| boj_bop_monthly.json | 財務省・日本銀行「国際収支統計」月次 1996年1月〜2026年9月（BP01、系列コードは 01_fetch.py の MONTHLY） | https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db=BP01&code=BPBP6JYNCB,...&startDate=199601&endDate=202609 | 148b3b1803ee |
| boj_bop_annual_1985_2013.json | 同 年次（6版組替）主要項目 1985〜2013年 | https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db=BP01&code=BPBP6RACYJYNCB,...&startDate=1985&endDate=2013 | b17c19565d1a |
| boj_usdjpy_monthly.json | 日本銀行「外国為替相場」東京市場 ドル・円 17時時点 月中平均（FM08 FXERM07）1985年1月〜 | https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db=FM08&code=FXERM07&startDate=198501&endDate=202609 | 8ed8ad2a6bb6 |

- 単位は億円（ドル円は円）。月次の最新月は速報で、今後改定される。
- 日本銀行 時系列統計データ検索サイト：https://www.stat-search.boj.or.jp/

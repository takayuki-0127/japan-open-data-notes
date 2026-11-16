# SOURCES（元データの取得元）

取得日：2026-11-16（src/01_fetch.py と同じ URL から取得）

| ファイル | 中身 | URL | sha256 の先頭12字 |
|---|---|---|---|
| boj_bop_monthly.json | 財務省・日本銀行「国際収支統計」月次 1996年1月〜2026年9月（BP01、系列コードは 01_fetch.py の MONTHLY） | https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db=BP01&code=BPBP6JYNCB,...&startDate=199601&endDate=202609 | 006962a6fecc |
| boj_usdjpy_monthly.json | 日本銀行「外国為替相場」東京市場 ドル・円 17時時点 月中平均（FM08 FXERM07） | https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db=FM08&code=FXERM07&startDate=199601&endDate=202609 | 5f4b30ae6684 |

- 単位は億円。月次の最新月は速報で、今後改定される。

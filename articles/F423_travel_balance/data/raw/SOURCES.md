# SOURCES（元データの取得元）

取得日：2026-11-16（src/01_fetch.py と同じ URL から取得）

| ファイル | 中身 | URL | sha256 の先頭12字 |
|---|---|---|---|
| boj_services_monthly.json | 財務省・日本銀行「国際収支統計」月次 サービス収支・輸送・旅行（受取・支払・業務・業務外）・その他サービス 1996年1月〜2026年9月 | https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db=BP01&code=BPBP6JYNSN,...&startDate=199601&endDate=202609 | 08c089c7682b |
| boj_usdjpy_monthly.json | 日本銀行「外国為替相場」ドル・円 17時時点 月中平均（FM08 FXERM07） | https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db=FM08&code=FXERM07&startDate=199601&endDate=202609 | 033c31b8bda8 |
| jnto_visitors_2003_2026.xlsx | 日本政府観光局「国籍/月別 訪日外客数（2003年～2026年）」（2026年10月21日掲載版） | https://www.jnto.go.jp/statistics/data/_files/20261021_1615-5.xlsx | e6cd0aadd774 |

- 国際収支の単位は億円。月次の最新月は速報。訪日外客数の最近の月は推計値・暫定値を含む。

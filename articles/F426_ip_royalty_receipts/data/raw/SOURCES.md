# SOURCES（元データの取得元）

取得日：2026-11-16（src/01_fetch.py と同じ URL から取得）

| ファイル | 中身 | URL | sha256 の先頭12字 |
|---|---|---|---|
| boj_ip_monthly.json | 財務省・日本銀行「国際収支統計」月次 知的財産権等使用料（産業財産権・著作権の内訳、受取・支払・ネット）とサービスの受取 1996年1月〜2026年9月 | https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db=BP01&code=BPBP6JYNSC906,...&startDate=199601&endDate=202609 | a3f970888206 |
| boj_ip_region_quarterly.json | 同 四半期 知的財産権等使用料の受取 地域別（2014年1-3月期〜2026年4-6月期） | https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db=BP01&code=BPBP6QSC95,...&startDate=201401&endDate=202602 | 6d77cca60ca6 |
| boj_usdjpy_monthly.json | 日本銀行「外国為替相場」ドル・円 17時時点 月中平均（FM08 FXERM07） | https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db=FM08&code=FXERM07&startDate=199601&endDate=202609 | a7de57ab663a |

- 単位は億円。最新の月・四半期は速報で、今後改定される。

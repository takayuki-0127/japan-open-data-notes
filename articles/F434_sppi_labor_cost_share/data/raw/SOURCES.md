# SOURCES（元データの取得元）

取得日：2026-11-16（src/01_fetch.py と同じ URL から取得）

| ファイル | 中身 | URL | sha256 の先頭12字 |
|---|---|---|---|
| boj_sppi_extax_monthly.json | 日本銀行「企業向けサービス価格指数」2020年基準 消費税を除く指数（総平均・除く国際運輸・高人件費率・低人件費率・大類別7、2000年1月〜2026年9月） | https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db=PR02&code=PRCS20_4200000000,...&startDate=200001&endDate=202609 | 6274664c9564 |
| boj_sppi_intax_monthly.json | 同 消費税を含む指数（総平均・高人件費率・低人件費率、1985年1月〜2026年9月） | https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db=PR02&code=PRCS20_5200000000,PRCS20_52S0000002,PRCS20_52S0000003&startDate=198501&endDate=202609 | f28238e9cb85 |

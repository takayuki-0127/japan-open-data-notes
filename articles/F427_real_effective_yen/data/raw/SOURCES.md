# SOURCES（元データの取得元）

取得日：2026-11-16（src/01_fetch.py と同じ URL から取得）

| ファイル | 中身 | URL | sha256 の先頭12字 |
|---|---|---|---|
| boj_effective_monthly.json | 日本銀行「実効為替レート」名目・実質（2020年＝100）と更新停止の旧系列（1973年3月＝100、2010年1月まで）、月次 1970年1月〜2026年9月 | https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db=FM09&code=FX180110001,FX180110002,FXCP7JP,FXCP8JP&startDate=197001&endDate=202609 | 188b59b79d89 |
| boj_usdjpy_monthly.json | 日本銀行「外国為替相場」ドル・円 17時時点 月中平均（FM08 FXERM07） | https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db=FM08&code=FXERM07&startDate=197001&endDate=202609 | f460febdd505 |

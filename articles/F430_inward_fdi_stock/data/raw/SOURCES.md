# SOURCES（元データの取得元）

取得日：2026-11-16（src/01_fetch.py と同じ URL から取得。GDP の CSV は F358 と同じファイル）

| ファイル | 中身 | URL | sha256 の先頭12字 |
|---|---|---|---|
| boj_iip_annual.json | 財務省・日本銀行「本邦対外資産負債残高」年末 1996〜2025年（直接投資の資産・負債と内訳、時価の推計値、資産・負債の計。十億円） | https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db=BP01&code=BPBP6KL1,...&startDate=1996&endDate=2025 | 17ec3f0edb8d |
| boj_fdi_region_annual.json | 同「直接投資残高地域別（負債）」2014〜2025年（億円） | https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db=BP01&code=BPBP6M1,...&startDate=2014&endDate=2025 | d521ab8256b5 |
| boj_fdi_flow_monthly.json | 同「国際収支統計」金融収支 直接投資（負債）ネットと内訳、月次 1996〜2025年（億円） | https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db=BP01&code=BPBP6JYNFL13,...&startDate=199601&endDate=202512 | 3dccf701df10 |
| esri_gaku-mcy2532.csv | 内閣府「四半期別GDP速報」2025年7-9月期2次速報（2020年基準）名目暦年 | https://www.esri.cao.go.jp/jp/sna/data/data_list/sokuhou/files/2025/qe253_2/tables/gaku-mcy2532.csv | 6353cd9bd515 |

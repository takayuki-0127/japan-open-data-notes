# SOURCES（元データの取得元）

取得日：2026-11-16（01_fetch.py で取得）

| ファイル | 中身 | URL | sha256 の先頭12字 |
|---|---|---|---|
| boj_stage_2015base.json | 企業物価指数 2015年基準 需要段階別・用途別指数（素原材料・中間財・最終財など、月次） | https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db=PR01&code=PRCG15_18K0110000,PRCG15_18K0210000,PRCG15_18K0310000,PRCG15_18K0322002,PRCG15_18K0321001,PRCG15_18K0000000,PRCG15_18K0121001,PRCG15_18K0221001&startDate=196001&endDate=202204 | 6cc77deffa5e |
| boj_fdid_2020base.json | 最終需要・中間需要物価指数 2020年基準（ステージ1〜4、最終需要（除く輸出）、月次） | https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db=PR04&code=PRFI20_1I1A00000,PRFI20_1I1G00000,PRFI20_1I1LD0000,PRFI20_1I2A00000,PRFI20_1I2G00000,PRFI20_1I2LD0000,PRFI20_1I3A00000,PRFI20_1I3G00000,PRFI20_1I3LD0000,PRFI20_1I4A00000,PRFI20_1I4G00000,PRFI20_1I4LD0000,PRFI20_1FXA00000,PRFI20_1FXG00000,PRFI20_1FXG00100,PRFI20_1FXG00200,PRFI20_1FXG00300,PRFI20_1FXSD0000&startDate=201501&endDate=202609 | 8deb5b49a29c |
| cpi_goods_services_1970_2026.csv | 消費者物価指数 2020年基準 財・サービス分類指数（全国、月次、1970年1月〜2026年9月） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000032103845&fileKind=1 | bbf3b7f663b9 |

出典：日本銀行「企業物価指数」「最終需要・中間需要物価指数」（時系列統計データ検索サイトの API）、総務省「消費者物価指数」（e-Stat）。CPI の CSV は Shift_JIS（cp932）。

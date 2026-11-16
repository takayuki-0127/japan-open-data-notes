# 元データの出典（取得日と URL）

取得日：2026-11-16（01_fetch.py で取得）

| ファイル | 中身 | URL | sha256 の先頭12字 |
|---|---|---|---|
| PRCS20_5200000000.csv | 企業向けサービス価格指数（2020年基準） 総平均（月次） | https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=csv&lang=jp&db=PR02&code=PRCS20_5200000000 | 067077c152c9 |
| PRCS20_52B0000000.csv | 同 総平均（除く国際運輸）（月次） | https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=csv&lang=jp&db=PR02&code=PRCS20_52B0000000 | 700fba03997b |
| PRCS20_5200630002.csv | 同 小類別 道路貨物輸送（月次） | https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=csv&lang=jp&db=PR02&code=PRCS20_5200630002 | f96f476f913b |
| PRCS20_5200650002.csv | 同 品目 宅配便・メール便（月次） | https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=csv&lang=jp&db=PR02&code=PRCS20_5200650002 | 237d66e9fab4 |
| PRCS20_5200650003.csv | 同 品目 自動車貨物輸送（農林水産・食料工業品）（月次） | https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=csv&lang=jp&db=PR02&code=PRCS20_5200650003 | cbf3c52b13ee |
| PRCS20_5200650004.csv | 同 品目 自動車貨物輸送（鉱産品・化学工業品）（月次） | https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=csv&lang=jp&db=PR02&code=PRCS20_5200650004 | c1b47ea48383 |
| PRCS20_5200650005.csv | 同 品目 自動車貨物輸送（金属機械工業品）（月次） | https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=csv&lang=jp&db=PR02&code=PRCS20_5200650005 | ec72dd5f71c9 |
| PRCS20_5200650006.csv | 同 品目 自動車貨物輸送（軽・雑工業品）（月次） | https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=csv&lang=jp&db=PR02&code=PRCS20_5200650006 | fd9e5309e25a |
| PRCS20_5200630001.csv | 同 小類別 鉄道貨物輸送（月次） | https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=csv&lang=jp&db=PR02&code=PRCS20_5200630001 | 1f205fab6e42 |
| PRCS20_5200730002.csv | 同 小類別 内航貨物輸送（月次） | https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=csv&lang=jp&db=PR02&code=PRCS20_5200730002 | 660ce9f12359 |
| PRCS20_5200930001.csv | 同 小類別 倉庫（月次） | https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=csv&lang=jp&db=PR02&code=PRCS20_5200930001 | 9edc8bd93799 |
| PRCG20_2200650005.csv | 国内企業物価指数（2020年基準） 品目 軽油（月次） | https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=csv&lang=jp&db=PR01&code=PRCG20_2200650005 | 8f06cb35da05 |

- 出典：日本銀行「企業向けサービス価格指数」「企業物価指数」（時系列統計データ検索サイトの API）。
- CSV は Shift_JIS（cp932）。先頭に API の応答の情報（STATUS など）の行がある。
- 指数は消費税を除くベース（企業向けサービス価格指数）。

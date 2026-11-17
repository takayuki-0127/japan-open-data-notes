# SOURCES（元データの取得元）

取得日：2026-11-16（01_fetch.py で取得）

| ファイル | 中身 | URL | sha256 の先頭12字 |
|---|---|---|---|
| d61ca.csv | 貿易統計 輸入 世界 年別 主要商品別（金額・数量） | https://www.customs.go.jp/toukei/suii/html/data/d61ca.csv | e167b67edf24 |
| d62ca004.csv | 貿易統計 輸入 中国 年別 主要商品別 | https://www.customs.go.jp/toukei/suii/html/data/d62ca004.csv | 88accd8cf52c |
| d62ca006.csv | 貿易統計 輸入 ASEAN 年別 主要商品別 | https://www.customs.go.jp/toukei/suii/html/data/d62ca006.csv | e13885744a28 |
| d62ca001.csv | 貿易統計 輸入 米国 年別 主要商品別 | https://www.customs.go.jp/toukei/suii/html/data/d62ca001.csv | f430a119efec |
| boj_fxerm07.csv | 日本銀行 東京市場 ドル・円 スポット 17時時点/月中平均（FXERM07、1988年1月〜2025年12月） | https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=csv&lang=jp&db=FM08&code=FXERM07&startDate=198801&endDate=202512 | bc9de5eca516 |

- 財務省貿易統計 輸出入額の推移：https://www.customs.go.jp/toukei/suii/html/time.htm
- 日本銀行 時系列統計データ検索サイト：https://www.stat-search.boj.or.jp/

出典：財務省「貿易統計」、日本銀行「外国為替市況」。CSV は Shift_JIS（cp932）。

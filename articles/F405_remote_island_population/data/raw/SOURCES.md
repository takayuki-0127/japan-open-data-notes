# data/raw の出典

取得日：2026-11-18（`src/01_fetch.py` で取得）。e-Stat の URL の形：`https://www.e-stat.go.jp/stat-search/file-download?statInfId=<statInfId>&fileKind=0`

| ファイル | 中身 | 取得元 |
|---|---|---|
| census_2025_main_000040507382.xlsx | 令和7年国勢調査 都道府県・市区町村別の主な結果（人口、2020年の組替人口、年齢3区分） | e-Stat statInfId 000040507382 |
| census_2020_main_000032143614.xlsx | 令和2年国勢調査 都道府県・市区町村別の主な結果（人口、2015年の組替人口、年齢3区分） | e-Stat statInfId 000032143614 |
| census_2015_main_000031594311.xls | 平成27年国勢調査 都道府県・市区町村別主要統計表（人口、2010年の組替人口、年齢3区分、大都市圏・都市圏） | e-Stat statInfId 000031594311 |
| mlit_ritou_list_R8_001886615.pdf | 国土交通省「離島振興対策実施地域一覧」（令和8年4月1日現在。島ごとの面積と令和2年国勢調査の人口） | https://www.mlit.go.jp/kokudoseisaku/chirit/content/001886615.pdf |
| mlit_ritou_list_R8_001886615.txt | 上の PDF を `pdftotext -layout`（poppler）で文字にしたもの。02 以降はこれを使う | 01_fetch.py で作成 |

離島の市町村（35）は、この一覧の島だけで町全体ができている市町村で、島の人口の合計を作成者が PDF から足し、`src/02_build.py` の中で2020年の人口と一致することを確かめています（大崎上島町だけ 33人の差）。

# SOURCES（元データの取得元）

取得日：2026-11-19（src/01_fetch.py と同じ URL から取得）。いずれも政府統計の総合窓口 e-Stat の掲載ファイル。

| ファイル | 中身 | URL | sha256 の先頭12字 |
|---|---|---|---|
| ecensus2009_basic_t1.xls | 平成21年経済センサス‐基礎調査 表1 産業（小分類），経営組織（２区分）別事業所数及び従業者数－全国，都道府県（「民営事業所」のシートを使用） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000012510098&fileKind=0 | 7de924a898bd |
| ecensus2014_basic_t2.csv | 平成26年経済センサス‐基礎調査 表2 産業（小分類）、経営組織（５区分）別全事業所数、男女別従業者数及び１事業所当たり従業者数－全国、都道府県（CSV、cp932。「うち民営」の列を使用） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031332477&fileKind=1 | 17c32ca35ebd |
| ecensus2016_activity_t4.csv | 平成28年経済センサス‐活動調査 表4 産業(中分類)，経営組織(７区分)別民営事業所数及び従業上の地位(６区分)，男女別従業者数―全国，都道府県，大都市（CSV、cp932。「総数(経営組織)」の列を使用） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031724996&fileKind=1 | f675b973d2f4 |
| ecensus2021_activity_t2_1.xlsx | 令和3年経済センサス‐活動調査 表2-1 産業(中分類)、経営組織(8区分)別全事業所数、男女別従業者数及び常用雇用者数－全国、都道府県、大都市（「1_民営」の行を使用） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040067802&fileKind=0 | 0945bda1e32e |
| ecensus2024_basic_t2.xlsx | 令和6年経済センサス‐基礎調査 表2 産業(中分類)、経営組織(7区分)別民営事業所数、従業者数及び常用雇用者数(雇用者のいない個人経営の事業所を除く)－全国、都道府県、大都市（「0_総数」の行を使用） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040389322&fileKind=0 | 134090b35c29 |
| pop_pref_2000_2020.xlsx | 総務省「人口推計」長期時系列 第5表 都道府県別人口（各年10月1日現在、2000〜2020年、千人） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000013168605&fileKind=4 | 9e28da4c0ef8 |
| pop_pref_2020_2024.xlsx | 総務省「人口推計」2024年 第5表 都道府県、男女別人口（各年10月1日現在、2020〜2024年、千人） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040268859&fileKind=0 | aec6333067aa |

- 一覧：基礎調査 https://www.e-stat.go.jp/stat-search/files?toukei=00200552 、活動調査 https://www.e-stat.go.jp/stat-search/files?toukei=00200553
- 産業は見出しの文字で選んだ：「62 銀行業」「63 協同組織金融業」、小分類のある年は「622 銀行（中央銀行を除く）」「631 中小企業等金融業」「632 農林水産金融業」。地域は表の地域の見出し（空白を除く）を、人口推計の都道府県名と照らして付けた（2021・2024年は地域コードの下3桁が000の行だけ）。
- 全年・全産業で、都道府県の合計が全国の値と一致することを確かめた（results/build_checks.csv）。北海道・青森県・東京都・沖縄県の値は元の表と目で照らした。

# SOURCES（元データの取得元）

取得日：2026-11-19（src/01_fetch.py で取得）

| ファイル | 中身 | URL | sha256 の先頭12字 |
|---|---|---|---|
| ts05_age3_pref_1920_2020.xlsx | 時系列データ 第5表 年齢（3区分）別人口及び年齢別割合－全国、都道府県（1920〜2020年）。2015・2020年は不詳補完値（※）の行もある | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000012993808&fileKind=0 | 9addf766037b |
| ts04_marital_national_1920_2020.xlsx | 時系列データ 第4表 配偶関係（4区分）、年齢（5歳階級）、男女別15歳以上人口－全国（1920〜2020年）。2015・2020年は不詳補完値（※）の行もある | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000001085974&fileKind=0 | 67355c40b794 |
| r7_t2-3_age_pref_original.xlsx | 令和7年国勢調査 人口等基本集計 第2-3表 男女、年齢（5歳階級及び3区分）別人口－全国、都道府県ほか【原数値】 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040506427&fileKind=0 | d0d25e19f05c |
| r7_t2-3_age_pref_imputed.xlsx | 令和7年国勢調査 人口等基本集計 第2-3表（同上）【不詳補完値】 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040506655&fileKind=0 | 16055f806d89 |
| r2retro_t2-3_age_pref_imputed.xlsx | 令和7年国勢調査の公表に合わせた 令和2年国勢調査の不詳補完値（遡及集計）第2-3表 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040317622&fileKind=0 | af086c83d358 |
| r7_t4-1_marital_pref_original.xlsx | 令和7年国勢調査 人口等基本集計 第4-1表 男女、年齢（各歳）、配偶関係別人口（15歳以上）－全国、都道府県ほか【原数値】 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040506436&fileKind=0 | 41da272fa16a |

- 統計表一覧：国勢調査 https://www.e-stat.go.jp/stat-search/files?toukei=00200521
- 出典：総務省統計局「国勢調査」（e-Stat）。出典を示して加工して使う。

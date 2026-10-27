# 元データ（data/raw/）

いずれも厚生労働省「人口動態統計」2025年確定数（e-Stat、2026年9月30日公開）の表から、該当する行・列を書き出したものです。

| ファイル | 中身 | 出典・URL | 期間 |
|---|---|---|---|
| births_monthly_2000_2025.csv | 出生数（年計と1〜12月） | 上巻 出生 第4.2表「出生月別にみた年次別出生数及び出生率（人口千対）」、e-Stat statInfId=000040503641（https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040503641&fileKind=1） | 2000〜2025年 |
| marriages_monthly_2000_2025.csv | 婚姻件数（年計と届出月別） | 上巻 婚姻 第9.3表「届出月別にみた年次別婚姻件数及び百分率」、e-Stat statInfId=000040503695（https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040503695&fileKind=1） | 2000〜2025年 |
| births_pref_annual.csv | 都道府県別の出生数（code は都道府県コード） | 上巻 出生 第4.3表「都道府県別にみた年次別出生数」、e-Stat statInfId=000040503642（https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040503642&fileKind=1） | 2010年、2014〜2025年（表に載っている年） |

確認：月の合計は年計と一致します。都道府県の合計は全国より 15〜125 人少なく、これは住所が外国・不詳の分です。

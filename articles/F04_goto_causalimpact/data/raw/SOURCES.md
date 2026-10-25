# 元データ

| ファイル | 内容 | 入手先 |
|---|---|---|
| `lodging_pref_monthly_2011_2025.csv` | 都道府県×月の延べ宿泊者数（total）・日本人（japanese）・外国人（foreign）、2011年1月〜2025年12月（確定値）、単位：人泊 | 観光庁「宿泊旅行統計調査」推移表（https://www.mlit.go.jp/kankocho/tokei_hakusyo/shukuhakutokei.html の「推移表」Excel）の旧1-2・旧2-2・旧3-2 シート（2025年12月以前調査分、月別）を縦長に並べ替えたもの |
| `covid_newly_confirmed_cases_daily.csv` | 都道府県別の新規陽性者数（日別、2020年1月16日〜2023年5月8日） | 厚生労働省「データからわかる－新型コロナウイルス感染症情報－」オープンデータ（https://covid19.mhlw.go.jp/public/opendata/newly_confirmed_cases_daily.csv） |

緊急事態宣言の日数の割合は、東京都の発令期間をもとに `src/common.py` の `EMERG` に直接書いています（2020年4月7日〜5月25日、2021年1月8日〜3月21日、4月25日〜6月20日、7月12日〜9月30日）。

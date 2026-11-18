# 自分での点検（F384、2026-11-18）

| 項目 | 条件 | 結果 |
|---|---|---|
| 再現 | /tmp に写して run_all.sh、results と figures が全部 cmp で一致。10分以内 | ○ 15ファイル一致（results 8・figures 4・data 3）、6秒 |
| 同梱 | data/raw にデータと SOURCES.md。オフラインで流れる | ○ Excel 21本＋CPI の CSV、13MB。02 以降はネットを使わない |
| 計画 | PLAN.md が分析より前、仮説ごとの判定が README にある | ○ H1 支持・H2 支持・H3 外れ・H4 支持 |
| 頑健性 | 3つ以上、表で | ○ 6通り（表） |
| 言えないこと | 4点以上 | ○ 5点 |
| 問い直し | 1つ以上 | ○ 同じ生まれ年の層を10年追う（03b） |
| 図 | 3〜4枚、日本語、出典の行、目で確かめた | ○ 4枚。Read で見て、重なった数字のラベルを直した |
| 数字の一致 | 題名・README・note の数字が results の値と一致 | ○ main.json・growth_by_age.csv・requestion.json・robustness.csv と照合 |
| 書かないこと | 扱わない話題・助言・悪い順の順位・名前がない | ○ 年齢は若い順、品目は表の順。助言なし |
| 重なり | 既存の看板記事と同じ問いでない | ○ 菓子の支出を扱う看板記事はなし（existing_F_titles.txt と jodn/articles を確認。F513 は米とパン） |

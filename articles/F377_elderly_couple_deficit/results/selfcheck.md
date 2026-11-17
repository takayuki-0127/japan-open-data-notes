# 自分で点検（2026-11-17）

| 項目 | 条件 | 結果 |
|---|---|---|
| 再現 | /tmp に写して run_all.sh、results と figures が全部 cmp で一致。10分以内 | 満たす（repro_check.txt） |
| 同梱 | data/raw にデータと SOURCES.md。オフラインで流れる | 満たす（run_all.sh は 01_fetch.py を呼ばない） |
| 計画 | PLAN.md が分析より前に書かれ、仮説ごとの判定が README にある | 満たす（前の担当は PLAN.md を書いていなかった。引き継いだ担当が集計の前に書き、見た範囲を開示） |
| 頑健性 | 3つ以上、表で | 満たす |
| 言えないこと | 4点以上 | 満たす |
| 問い直し | 1つ以上 | 満たす（03b_requestion.py） |
| 図 | 3〜4枚、日本語が出ている、出典の行、目で確かめた | 満たす（4枚、PNG を目で確認） |
| 数字の一致 | 題名・README・note の数字が results の値と一致（丸めの範囲） | 満たす（README・note の数字を results の JSON・CSV と機械で照合。報告書の「約1,300万円」は引用） |
| 書かないこと | 扱わない話題・助言・悪い順の順位・名前がない | 満たす |
| 重なり | 既存の看板記事と同じ問いでない | 満たす（existing_F_titles.txt と /home/claude/jodn/articles を確認） |

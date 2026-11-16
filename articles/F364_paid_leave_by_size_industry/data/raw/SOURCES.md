# SOURCES（元データの取得元）

取得日：2026-11-16（src/01_fetch.py で取得）。

| ファイル | 中身 | URL | sha256 の先頭12字 |
|---|---|---|---|
| fetch_log.tsv | 01_fetch.py の取得記録（statInfId・大きさ・ハッシュ） |  | bb31a54fb000 |
| ts11_granted_days.xls | 厚生労働省「就労条件総合調査」時系列表 11 企業規模・産業別、労働者1人平均年次有給休暇の付与日数（1984〜2025年調査） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040425819&fileKind=4 | bccef1d33375 |
| ts12_taken_days.xls | 同 時系列表 12 取得日数 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040425820&fileKind=4 | 67ea2fd21b38 |
| ts13_take_rate.xls | 同 時系列表 13 取得率 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040425821&fileKind=4 | 05e204c23c4d |

出典：厚生労働省「就労条件総合調査」（e-Stat）

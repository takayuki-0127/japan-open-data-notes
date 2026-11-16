# SOURCES（元データの取得元）

取得日：2026-11-16（src/01_fetch.py で取得）。

| ファイル | 中身 | URL | sha256 の先頭12字 |
|---|---|---|---|
| fetch_log.tsv | 01_fetch.py の取得記録（statInfId・大きさ・ハッシュ） |  | ad0c6dd42e78 |
| jobs_to_applicants_ratio_longterm.xlsx | 厚生労働省「一般職業紹介状況」長期時系列表 3 有効求人倍率（パートを含む、実数・季節調整値、2026年9月分まで） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040518983&fileKind=0 | c7942b164fa8 |
| lfs_reason_2013_2017.xls | 総務省「労働力調査」年報 詳細集計 全国・時系列表 II-A-4 年齢階級，現職の雇用形態についた主な理由別非正規の職員・従業員数（2017年版、2013〜2017年） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031702919&fileKind=0 | 287c93ca09e0 |
| lfs_reason_2018_2022.xlsx | 同 II-A-3（2022年版、2018〜2022年） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040058529&fileKind=0 | a91d443e42bf |
| lfs_reason_2021_2025.xlsx | 同 II-A-3（2025年版、2021〜2025年） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040440965&fileKind=0 | 71221c79a4f6 |

出典：総務省「労働力調査」、厚生労働省「一般職業紹介状況」（e-Stat）

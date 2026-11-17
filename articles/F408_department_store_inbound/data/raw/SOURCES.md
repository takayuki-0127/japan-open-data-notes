# SOURCES（元データの取得元）

取得日：2026-11-18（src/01_fetch.py で取得）

| ファイル | 中身 | URL | sha256 の先頭12字 |
|---|---|---|---|
| meti_dept_super_timeseries.xlsx | 経済産業省「商業動態統計」時系列データ 百貨店・スーパー商品別販売額等（月次・年、1980年〜2026年9月） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031387994&fileKind=0 | 3ee307c02604 |
| meti_pref_2019.xls | 経済産業省「商業動態統計」参考表（年報）2019年 第3部第3表 都道府県別、百貨店・スーパー別、商品別販売額等 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031960815&fileKind=0 | 2cc60ec0295b |
| meti_pref_2025.xlsx | 経済産業省「商業動態統計」参考表（年報）2025年 第2表 都道府県別、百貨店・スーパー別、商品別販売額等 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040471260&fileKind=0 | a94c32760705 |
| jnto_visitors_2003_2026.xlsx | 日本政府観光局（JNTO）「国籍/月別 訪日外客数（2003年～2026年）」（2026年10月21日掲載版） | https://www.jnto.go.jp/statistics/data/_files/20261021_1615-5.xlsx | e6cd0aadd774 |
| cpi_item_annual.csv | 総務省「消費者物価指数」2025年基準 全国 品目別価格指数。**年度平均**の表（2025年の総合が100.4）で、暦年の年平均ではなかったため、レビュー（2026-11-18）以降は使っていない（記録として残す） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040482959&fileKind=1 | 7ce020001725 |
| cpi_annual_middle_class.csv | 総務省「消費者物価指数」2025年基準 全国 中分類指数（暦年の年平均、1970〜2025年、CSV、Shift_JIS）。2026-11-18 のレビューで取得して追加し、物価はこの表を使う | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040482829&fileKind=1 | f639475ca393 |
| kanko_2019_annual.xls | 観光庁「訪日外国人消費動向調査」2019年 集計表（暦年・確報） | https://www.mlit.go.jp/kankocho/content/002020401.xls | b6399545d0ab |
| kanko_2023_annual.xls | 観光庁「インバウンド消費動向調査」2023年 集計表（暦年・確報） | https://www.mlit.go.jp/kankocho/content/002020300.xls | f2b70436322c |
| kanko_2024_annual.xls | 観光庁「インバウンド消費動向調査」2024年 集計表（暦年・確報） | https://www.mlit.go.jp/kankocho/content/002022649.xls | 678aa74cd3c0 |
| kanko_2025_annual.xls | 観光庁「インバウンド消費動向調査」2025年 集計表（暦年・確報） | https://www.mlit.go.jp/kankocho/content/002025515.xls | c5451c6d5f88 |

- e-Stat の一覧：https://www.e-stat.go.jp/stat-search/files?toukei=00550030 （商業動態統計調査。時系列データと参考表（年報））
- 観光庁の一覧：https://www.mlit.go.jp/kankocho/tokei_hakusyo/gaikokujinshohidoko.html
- 注：消費者物価指数の statInfId=000040482959（品目別）・000040482957（中分類）は年度平均の表。暦年の年平均は 000040482829（中分類）を使う。
- 日本百貨店協会の免税売上の統計は、取得を試みたが接続できなかったため使っていない（2026-11-18）。

出典：経済産業省「商業動態統計」（e-Stat）、日本政府観光局「訪日外客数」、観光庁「訪日外国人消費動向調査」「インバウンド消費動向調査」。

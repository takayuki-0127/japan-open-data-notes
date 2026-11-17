# SOURCES（元データの取得元）

取得日：2026-11-18（01_fetch.py で取得）

| ファイル | 中身 | URL | sha256 の先頭12字 | バイト |
|---|---|---|---|---|
| cci_t2_sa.xlsx | 消費動向調査 長期時系列表 2表 消費者態度指数・消費者意識指標（二人以上の世帯、季節調整値、1982年6月〜2026年10月） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040522411&fileKind=0 | 19186d17568b | 55208 |
| cci_t1_orig.xlsx | 消費動向調査 長期時系列表 1表 消費者態度指数・消費者意識指標（二人以上の世帯、原数値） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040522412&fileKind=0 | 79ceaa11a15f | 53026 |
| qe_gaku-jk2631.csv | 四半期別GDP速報 2026年7-9月期1次速報 実質季節調整系列 実額（2020暦年連鎖価格、1994年1-3月期〜） | https://www.esri.cao.go.jp/jp/sna/data/data_list/sokuhou/files/2026/qe263/tables/gaku-jk2631.csv | 0e2733c14fea | 42826 |
| qe_kgaku-jk2631.csv | 四半期別GDP速報 2026年7-9月期1次速報 実質季節調整系列 家計最終消費支出の形態別 実額 | https://www.esri.cao.go.jp/jp/sna/data/data_list/sokuhou/files/2026/qe263/tables/kgaku-jk2631.csv | e17109cb5310 | 25559 |
| kakei_ts2_youto_monthly.xlsx | 家計調査 長期時系列 表2 用途分類（二人以上の世帯、月・四半期・年、2000年〜） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040270657&fileKind=4 | 4c4fffb6432d | 1292103 |
| cpi_2025base_middle_class_monthly.csv | 消費者物価指数 2025年基準 全国 中分類指数（月次、1970年1月〜、cp932） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040482943&fileKind=1 | 29b63b7aa5cb | 279236 |

- 消費動向調査のファイル一覧：https://www.e-stat.go.jp/stat-search/files?toukei=00100405&tstat=000001014549（長期時系列表は最新月の公表分に入る。月が進むとファイル番号が変わる）
- 四半期別GDP速報：https://www.esri.cao.go.jp/jp/sna/data/data_list/sokuhou/files/2026/qe263/gdemenuja.html（CSV は Shift_JIS）
- 家計調査 長期時系列：https://www.e-stat.go.jp/stat-search/files?toukei=00200561
- 消費者物価指数：https://www.e-stat.go.jp/stat-search/files?tstat=000001243876

出典：内閣府「消費動向調査」、内閣府経済社会総合研究所「四半期別GDP速報」、総務省統計局「家計調査（家計収支編）」「消費者物価指数」。

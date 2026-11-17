# SOURCES（元データの取得元）

取得日：2026-11-16（src/01_fetch.py で取得）。

| ファイル | 中身 | URL | sha256 の先頭12字 |
|---|---|---|---|
| ci_coincident_series.xlsx | 内閣府「景気動向指数」一致系列の個別系列（C1 生産指数（鉱工業）など、1975年1月〜） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040520967&fileKind=0 | 5ff9e305f444 |
| esri_hiduke.html | 内閣府経済社会総合研究所「景気基準日付」ページ | https://www.esri.cao.go.jp/jp/stat/di/hiduke.html | 864d4d70df6a |
| fetch_log.tsv | 取得の記録（statInfId、バイト数、sha256、Content-Disposition） |  | db3ca680bf48 |
| maikin_sa_index.xlsx | 厚生労働省「毎月勤労統計調査」全国調査 長期時系列表 季節調整済指数（1998年1月〜、2020年=100） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040259772&fileKind=4 | 4782a46c05f7 |

出典：厚生労働省「毎月勤労統計調査」、内閣府「景気動向指数」「景気基準日付」（いずれも e-Stat・内閣府ウェブサイトから取得）

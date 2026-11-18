# SOURCES（元データの取得元）

取得日：2026-11-18（src/01_fetch.py で取得）

| ファイル | 中身 | URL | sha256 の先頭12字 | バイト数 |
|---|---|---|---|---|
| juchu_chouki1_2608.xlsx | 内閣府「機械受注統計調査」長期系列(1) 主要需要者別受注・販売・残高（季調・原系列、月次・四半期、2005年4月〜2026年8月） | https://www.esri.cao.go.jp/jp/stat/juchu/2026/2608chouki-1.xlsx | 28095d897401 | 187498 |
| qe_nominal_sa_2631.csv | 内閣府「四半期別GDP速報」2026年7-9月期 1次速報 名目季節調整系列（年率、10億円、1994年1-3月期〜） | https://www.esri.cao.go.jp/jp/sna/data/data_list/sokuhou/files/2026/qe263/tables/gaku-mk2631.csv | 429930065aa2 | 38450 |
| qe_real_sa_2631.csv | 同 実質季節調整系列（連鎖方式、年率、10億円） | https://www.esri.cao.go.jp/jp/sna/data/data_list/sokuhou/files/2026/qe263/tables/gaku-jk2631.csv | 0e2733c14fea | 42826 |
| qe_deflator_sa_2631.csv | 同 四半期デフレーター 季節調整系列 | https://www.esri.cao.go.jp/jp/sna/data/data_list/sokuhou/files/2026/qe263/tables/def-qk2631.csv | 2bed021c5e34 | 21167 |

- 機械受注統計の一覧と長期系列：https://www.esri.cao.go.jp/jp/stat/juchu/juchu.html
- 四半期別GDP速報の統計表一覧（2026年7-9月期 1次速報、2026年11月16日公表）：https://www.esri.cao.go.jp/jp/sna/data/data_list/sokuhou/files/2026/qe263/gdemenuja.html
- 機械受注の長期系列は2026年8月分（2026年10月公表）が取得時点の最新。季節調整は公表のたびにかけ直されるので、取り直すと過去の値も少し変わる。

出典：内閣府「機械受注統計調査」「四半期別GDP速報（国民経済計算）」。

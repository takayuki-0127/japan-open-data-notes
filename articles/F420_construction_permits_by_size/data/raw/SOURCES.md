# SOURCES（元データの取得元）

取得日：2026-11-16（src/01_fetch.py と同じ URL から取得）

| ファイル | 中身 | URL / 作り方 | sha256 の先頭12字 |
|---|---|---|---|
| mlit_kyoka_2025_03.pdf | 国土交通省「建設業許可業者数調査の結果について－建設業許可業者の現況（令和7年3月末現在）－」（2025年5月16日公表） | https://www.mlit.go.jp/report/press/content/001889275.pdf | 40fb95c2ba18 |
| table1_total.csv | 表－１ 建設業許可（登録）業者数の推移（1958〜2025年、大臣・知事別） | src/01b_extract.py で PDF から抜き出し（pdftotext 24.02.0 -layout） | e3edf9b40ed5 |
| table5_capital.csv | 表－５ 資本金階層別業者数の推移（1993〜2025年、9階層の業者数） | 同上。階層の合計＝総数、表－１の総数との一致を確かめ済み | 273efdb12ac9 |
| table3_by_type.csv | 表－３ 業種別許可業者数の推移（2000年、2011〜2025年、29業種と合計） | 同上。29業種の和＝合計を確かめ済み | 0efaacc17556 |

- 年は各年3月末現在。和暦は西暦に直した（平成12年＝2000年、令和7年＝2025年）。
- 報道発表のページ：https://www.mlit.go.jp/report/press/tochi_fudousan_kensetsugyo13_hh_000001_00296.html
- run_all.sh は抜き出し済みの CSV から作るので、pdftotext もネットも使わない。

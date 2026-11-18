# SOURCES（元データの取得元）

取得日：2026-11-18（src/01_fetch.py で取得）

| ファイル | 中身 | URL | sha256 の先頭12字 | バイト数 |
|---|---|---|---|---|
| mof_ssc_quarterly_all.xls | 法人企業統計調査 四半期別調査 時系列データ「All items」（全項目。設備投資・ソフトウェア・減価償却費・有形固定資産などを含む。億円、原数値、1954年4-6月期〜2026年4-6月期） | https://www.mof.go.jp/english/pri/reference/ssc/historical/all.xls | 70c5b3204644 | 2936320 |

- 掲載ページ（英語版の時系列データ）：https://www.mof.go.jp/english/pri/reference/ssc/historical.htm
  （日本語版の同じページ https://www.mof.go.jp/pri/reference/ssc/historical.htm は 2026-11-18 に 404 だった。数値は同じ調査の時系列表）
- 規模の区分：A 全規模、B 資本金10億円以上、C 1億円以上10億円未満、D 1千万円以上1億円未満（掲載ページの注記による）
- 業種：全産業（金融業・保険業を除く）、製造業、非製造業（金融業・保険業を除く）、全産業（金融業・保険業を含む）、金融業・保険業

出典：財務省「法人企業統計調査」。

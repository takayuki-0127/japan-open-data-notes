# 232 前年同月比と12か月移動平均を、SQL のウィンドウ関数で出す（実務の型）

月次の数字の「前年同月比」と「12か月移動平均」を、Excel や pandas に出さずに SQL だけで出す型を、経済産業省「商業動態統計」の業態別販売額（6業態、2014年1月〜2026年8月）で試したフォルダです。SQL は SQL Server（T-SQL）の書き方で書き、同じ文が DuckDB でも動くことを確かめて、pandas の計算と照合しました。

| # | 問い | 手法 | ファイル |
|---|---|---|---|
| A232 | 前年同月比・移動平均を、SQL のウィンドウ関数でどう出すか。月が抜けていたら何が起きるか | `LAG(sales, 12) OVER (PARTITION BY … ORDER BY …)`、`AVG(...) OVER (… ROWS BETWEEN 11 PRECEDING AND CURRENT ROW)`、日付で12か月前と結合する書き方、抜けた月の点検 | `sql/02_yoy_ma.sql`・`03_yoy_calendar.sql`・`04_check_gaps.sql`、`src/a232_window.py` |

## 主な結果
- 6業態×152か月（912行）で、SQL の前年同月比・12か月移動平均は pandas の `pct_change(12)`・`rolling(12).mean()` と完全に一致した（差の最大0）
- 前年同月比が出ない最初の12か月（72行）は NULL、移動平均の月数が12に満たない最初の11か月（66行）は `COUNT(*) OVER` で見分けて空けた
- 試しにコンビニの2020年5月の1行を消すと、`LAG(…, 12)` は「行の位置で12前」を取るため、2020年6月〜2021年5月の12か月の前年同月比がずれた（最大8.3ポイント、平均4.5ポイント）。日付で12か月前と結合する書き方（03）はずれ0で、抜けた月とその1年後だけが NULL になった
- 抜けた月は `04_check_gaps.sql`（前の行との間が1か月でない行を探す）で1件見つかった
- 2026年8月の前年同月比：ドラッグストア+3.1%、百貨店+1.9%、ホームセンター+1.3%、家電大型専門店+1.3%、スーパー+1.0%、コンビニ+0.6%

## 動かし方
```
pip install -r requirements.txt
cd src && python a232_window.py
```
`src/common.py` の `tsql_to_duckdb()` が、T-SQL の `DATEADD(month, …)`・`DATEDIFF(month, …)`・`CAST(… AS FLOAT)` を DuckDB の書き方に置き換えてから実行します（T-SQL の FLOAT は8バイト、DuckDB の FLOAT は4バイトのため DOUBLE に）。

## データ
- `data/meti_sales_monthly.csv`：業態別販売額（百万円）。コンビニ・スーパー・ドラッグストア・ホームセンター・家電大型専門店・百貨店の6業態、2014年1月〜2026年8月（F293 で取得したものの写し）
- `results/yoy_ma12_by_sql.csv`：SQL で出した前年同月比・12か月移動平均（`ma12_n` は平均した月数）
- `results/missing_month_test.csv`：1行消したときの、正しい値・LAG・日付結合の前年同月比とずれ
- `results/checks.json`：照合の結果

## 注意
- `sql/01_create_load.sql` の `BULK INSERT` と、T-SQL の `DATEADD`・`DATEDIFF` そのものは、この環境（SQL Server なし）では動かしていません（未検証）。`02`〜`04` は上の置き換えをして DuckDB で動かしました
- 販売額は名目の値で、物価の変化は除いていません。業態の定義や調査の対象が変わった月は、ならしていません
- 前年同月比は、うるう年や曜日の並び（土日の数）の違いを含みます
- 「抜けた月」の試しは、実際にデータが抜けていたのではなく、説明のために1行消したものです

## 出典
経済産業省「商業動態統計」（https://www.meti.go.jp/statistics/tyo/syoudou/）をもとに作成者が加工して作成

コード：MIT License

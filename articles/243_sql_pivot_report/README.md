# 243 縦長の統計表を、SQL でレポートの形（横長）にする（実務の型）

公的統計は「業態・月・値」のような縦長の形で配られることが多く、レポートでは「年×業態」のような横長の表にしたくなります。その形の変え方（CASE WHEN／PIVOT）と、形を変えたときに起きる落とし穴を、経済産業省「商業動態統計」の業態別販売額（6業態、2014年1月〜2026年8月、912行）で試したフォルダです。SQL は SQL Server（T-SQL）の書き方で書き、同じ文が動くものは DuckDB で動かして pandas と照合しました。

| # | 問い | 手法 | ファイル |
|---|---|---|---|
| A243 | 縦長の表を、年×業態のレポートの形にするには。形を変えると何が見えなくなるか | `SUM(CASE WHEN …)`、T-SQL の `PIVOT`、動的 SQL（`STRING_AGG`＋`sp_executesql`）、DuckDB の `PIVOT`／`UNPIVOT`、照合のクエリ | `sql/02`〜`05`、`src/a243_pivot.py` |

## 主な結果
- 2014〜2025年の12年×6業態の表は、CASE WHEN で作っても DuckDB の PIVOT で作っても pandas の `pivot_table` で作っても、すべての値が一致した（差の最大0）
- 落とし穴1：列にない業態が増えると、CASE WHEN（と列を手で書く T-SQL の PIVOT）は**その行を黙って落とす**。試しに架空の業態を2025年に12行足すと、縦長の合計と横長の列の合計が13,321億円ずれた。CASE WHEN の文に `COUNT(*)` を並べておくと、2025年だけ行数が72→84になり気づける。列を表から読む書き方（動的 SQL・DuckDB の PIVOT）は列が7本に増えた
- 落とし穴2：同じ月の行が2回入ると、PIVOT の `SUM` は黙って足す。コンビニの2025年3月を二重に入れると、コンビニの2025年が11,041億円多く出た。縦長の合計と横長の列の合計はどちらも同じだけ増えるので**この照合では見つからず**、キーの重複チェック（`GROUP BY … HAVING COUNT(*) > 1`）で1件見つかった
- 落とし穴3：月×年の横長の表（コンビニ、13年×12か月＝156セル）を縦に戻すと、2026年9〜12月の空いたセル4個は、普通の `UNPIVOT` では行ごと消え（152行＝元と同じ）、`INCLUDE NULLS` では残る（156行）。T-SQL の `UNPIVOT` は NULL のセルを必ず落とす（`INCLUDE NULLS` にあたる指定はない）。「0」と「まだ公表されていない」を区別したいときは、戻す前に空のセルを数えておく

## 動かし方
```
pip install -r requirements.txt
cd src && python a243_pivot.py
```
`src/common.py` の `tsql_to_duckdb()` が、T-SQL の `N'…'`・`DATEADD`・`DATEDIFF`・`CAST(… AS FLOAT)` を DuckDB の書き方に置き換えてから実行します。

## データ
- `data/meti_sales_monthly.csv`：業態別販売額（百万円）。6業態、2014年1月〜2026年8月（記事232・F293 で取得したものの写し）
- `results/wide_year_by_gyotai.csv`：年×業態の表（CASE WHEN の結果）
- `results/scenarios.csv`・`results/checks.json`：3つの落とし穴の試しと照合の結果

## 注意
- `sql/01_create_load.sql` の `BULK INSERT`、`sql/03`（T-SQL の PIVOT）、`sql/04`（動的 SQL）は SQL Server 専用の構文のため、この環境では動かしていません（未検証）。`02` と `05` は DuckDB で動かしました。DuckDB の PIVOT／UNPIVOT はスクリプトの中に書いています
- 「新しい業態」と「二重の行」は、説明のために足した試しの行で、元のデータにはありません
- 販売額は名目の値です

## 出典
経済産業省「商業動態統計」（https://www.meti.go.jp/statistics/tyo/syoudou/）をもとに作成者が加工して作成

コード：MIT License

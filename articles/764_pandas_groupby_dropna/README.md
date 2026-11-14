# 764 pandas の groupby が欠けたキーの行を黙って落とすと、合計はどれだけ減るのか（実務の型・pandas の集計）

pandas の `groupby` は、何も指定しないと、キーが欠けた（NaN の）行を集計から外します（`dropna=True` が既定）。エラーも警告も出ません。SQL の GROUP BY は欠けたキーを1つのまとまりとして残すので、SQL に慣れた人ほど気づきにくい違いです。**ここでは、架空の売上明細6万行（2年分、50店。店コードは基本1%、システムを入れ替えた2025年4月だけ20%の行で欠け、カテゴリも2%で欠ける）で、pandas の集計のしかたを変えて、全体の合計からどれだけ減るかを数えました。** 欠ける割合は作成者が置いたもので、数字はその置き方で決まります。

| # | 問い | 手法 | ファイル |
|---|---|---|---|
| A764 | groupby の既定で、欠けたキーの行はどれだけ合計から消えるか | groupby（既定）、groupby(dropna=False)、「未設定」で埋めてから groupby、店×カテゴリの groupby、pivot_table、value_counts。DuckDB（1スレッド）の GROUP BY が NULL を残すことも確認。seed 764 | `src/a764_dropna.py`、`src/02_groupby_duckdb.sql`、`src/01_groupby_tsql.sql`（未検証） |

## 主な結果
- **店別の groupby**：店コードの欠けた1,132行（1.89%）が消え、2年分の売上の1.85%が合計から落ちた
- **キーが2つになると増える**：店×カテゴリの groupby と pivot_table では、どちらかが欠けた2,345行が消え、3.92%が落ちた。value_counts も欠けた1,132行を数えない
- **欠けの多い月に集中する**：月×店で集計して月ごとに足すと、2025年4月だけ売上の19.3%が消えた（ほかの月は中央値1.0%）。2025年4月の前年同月比は、本当は+1.3%なのに−17.3%に見えた
- **直し方**：`dropna=False` か、先に `fillna("未設定")` で埋めると、どちらも合計と一致した。DuckDB の GROUP BY は NULL を1つのまとまりとして残した

## 動かし方
```
pip install -r requirements.txt
cd src && python a764_dropna.py
```
数秒で終わります。`data/sales_lines.csv` に売上明細を、`results/monthly.csv` に月ごとの本当の合計と groupby で足した合計を書き出します。

## 確かめたこと
- 空のフォルダで流し直し、data・results・figures がバイト単位で一致した（DuckDB は `SET threads=1`）
- dropna=False と「未設定」で埋めた場合の合計が、全体の合計と一致した
- DuckDB の GROUP BY の合計が全体と一致し、NULL の店の行数が pandas の欠けた行数と一致した
- pandas 2.3 で確かめた。T-SQL 版（`01_groupby_tsql.sql`）は書いたが、SQL Server では動かしていない（**未検証**）

## データ
- `data/sales_lines.csv`：ym・store・category・amount（欠けたキーは空欄）
- 仮定：毎月2,500行、店とカテゴリは無作為。金額は対数正規分布

## 注意（言えないこと）
- 架空のデータ。消える割合は、キーの欠けの多さで決まる
- pandas のバージョンによって既定や警告が変わることがある（推測）。集計の前に `isna().sum()` でキーの欠けを数えておくのが確実
- 実在の店の数字ではない

## 出典
架空の売上明細（作成者が乱数で作成、seed 764）

コード：MIT License

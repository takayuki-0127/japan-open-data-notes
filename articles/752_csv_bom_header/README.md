# 752 先頭に BOM のついた CSV を csv モジュールで読むと、最初の列名が一致せず、何行の売上が黙って集計から落ちるのか（実務の型・CSV の取り込み）

Excel などで「CSV UTF-8」として保存すると、ファイルの先頭に BOM（見えない3バイト EF BB BF）がつきます。Python の csv モジュールで `encoding="utf-8"` として読むと、BOM が最初の列名に残り、列名が `"store_id"` ではなく `"﻿store_id"` になります。`row.get("store_id")` のような書き方では、エラーにならずに None が返ります。**ここでは、架空の36店の日別売上を月ごとの CSV 24本（2024年1月〜2025年12月、2025年4月から BOM つき）に書き出し、4つの読み方で2年分の売上を店ごとに足しました。** BOM がつきはじめる月は作成者が置いたもので、数字はその置き方で決まります。

| # | 問い | 手法 | ファイル |
|---|---|---|---|
| A752 | BOM つきの CSV を csv モジュールで読むと、何行の売上が集計から落ちるか | A csv.DictReader（utf-8）で `row.get("store_id")`、B 同じく utf-8-sig、C pandas.read_csv、D DuckDB の read_csv（1スレッド）。B・C・D が本当の合計と一致することを確認。seed 752 | `src/a752_bom.py`、`src/02_bom_duckdb.sql`、`src/01_bom_tsql.sql`（未検証） |

## 主な結果
- **24本のうち9本（2025年4月〜12月）が BOM つき**。A の読み方では、その9本の9,900行（全体の37.6%）で店が分からなくなり、売上の37.6%が店ごとの集計から落ちた
- **エラーは出ない**：`row.get` は None を返すだけ。2025年だけで見ると75.2%が落ち、前年比は本当の+0.2%が−75.2%に見えた
- **画面では区別できない**：BOM つきの列名も print すると `store_id` と表示される。repr で見ると `'﻿store_id'`（9文字）
- **utf-8-sig・pandas・DuckDB は正しく読む**：3つとも2年分の合計が一致した（pandas と DuckDB は BOM を外して読む）

## 動かし方
```
pip install -r requirements.txt
cd src && python a752_bom.py
```
数秒で終わります。`data/` に CSV 24本と店のマスタを、`results/files.csv` にファイルごとの BOM の有無と読めた売上を書き出します。

## 確かめたこと
- 空のフォルダで流し直し、data・results・figures がバイト単位で一致した（DuckDB は `SET threads=1`）
- B（utf-8-sig）・C（pandas）・D（DuckDB）の合計が、書き出した売上の合計と一致した。A で落ちた行は BOM つきの9本の行数と一致した
- DuckDB で店のマスタと結べない行が0件であることを確かめた
- T-SQL 版（`01_bom_tsql.sql`、BULK INSERT と確かめの SQL）は書いたが、SQL Server では動かしていない（**未検証**）

## データ
- `data/sales_YYYYMM.csv`：store_id・date・sales（2025年4月以降は BOM つき）。`data/stores.csv`：store_id・area
- 仮定：36店、店の大きさはばらばら、土日は1.25倍。2年で売上はほぼ横ばい

## 注意（言えないこと）
- 架空のデータ。落ちる割合は、BOM つきのファイルが何本あるかで決まる
- ここで調べたのは Python 3 の csv モジュール・pandas 2.x・DuckDB 2.0。ほかの道具やバージョンでは扱いが違うことがある（推測）
- 実在の店の数字ではない

## 出典
架空の店別・日別の売上 CSV（作成者が乱数で作成、seed 752）

コード：MIT License

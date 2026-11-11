# データ辞書：サンプルマート（架空）の mart（F247）

**会社・数字はすべて架空（合成データ）。実在の会社とは関係がない。**
mart は `sql/10_staging.sql` → `sql/20_mart.sql` で作り、`sql/30_tests.sql` の9つのテストがすべて 0 のものだけを `mart/` に置いた。F248（ダッシュボード）・F249（需要の予測）はこのファイルを読む。

## 共通の決めごと
- 期間：2022-04-01〜2026-03-31（FY2022〜FY2025。年度は4月始まり）。
- 金額は円（税抜き、合成）。小数は端数の合計と、空の人時を埋めた日の人件費から出る。
- 店は `store_id`（1〜24）。POS の店コードは 2024-04 に振り直されたので、店コードではなく `store_id` で結合する。店コードとの対応は `dim_store_code_history`。
- 部門は `category_id`（1〜7）。2025-04 の部門の付け替え（7→8）と惣菜の分割（4→4と9）は、元の7部門に戻してある。
- 店×日の行は「その日に営業していた店」だけ。開店前・閉店後の行はない。

## fact_store_day.csv.gz（店×日、32,325 行）
キー：`biz_date`, `store_id`

| 列 | 型 | 意味 | 元のファイル・作り方 |
|---|---|---|---|
| biz_date | 日付 | 営業日 | POS 店×日の「営業日」 |
| store_id | 整数 | 店番（dim_store） | POS の店コード → 有効期間つきの対応表＋補正表 |
| receipts | 整数 | レシートの枚数（客数） | POS「レシート枚数」。再送は最新の1回だけ |
| member_receipts | 整数 | 会員カードを出したレシートの枚数 | POS「会員レシート枚数」 |
| items | 整数 | 買上点数の合計 | POS「点数」 |
| sales | 円 | 売上（税抜き） | POS「売上金額」 |
| gross_profit_before_waste | 円 | 粗利（廃棄前） | 部門×日の「粗利金額」の合計 |
| waste | 円 | 廃棄額 | 廃棄登録の合計。19店の 2025-06〜08 は千円で入力されていたので ×1000 |
| gross_profit | 円 | 粗利（廃棄後）＝ gross_profit_before_waste − waste | 計算 |
| labor_hours | 時間 | 人時（働いた時間の合計） | 勤怠「人時」。空の日は同じ店・同じ月・同じ曜日の平均で埋める |
| labor_cost | 円 | 人件費 | 勤怠「人件費」。空の日は 埋めた人時 × その店・月の時給 |
| labor_imputed | 0/1 | 1 ＝ 人時・人件費を埋めた日（460 店×日） | 計算 |

## fact_store_day_category.csv.gz（店×日×部門、226,275 行）
キー：`biz_date`, `store_id`, `category_id`

| 列 | 型 | 意味 |
|---|---|---|
| biz_date, store_id | | 上と同じ |
| category_id | 整数 | 部門（1〜7、dim_category） |
| sales | 円 | 部門の売上。店×日の sales との差は端数の丸め（10円以内、T07） |
| gross_profit_before_waste | 円 | 部門の粗利（廃棄前） |
| waste | 円 | 部門の廃棄額（廃棄登録がない日は 0） |

## store_month.csv（店×月、1,062 行）
キー：`ym`, `store_id`

| 列 | 意味 |
|---|---|
| ym, fy | 年月（YYYY-MM）、年度 |
| days_with_sales | その月に売上のある日数 |
| sales, receipts, member_receipts, items, gross_profit_before_waste, waste, gross_profit, labor_hours, labor_cost | 店×日の合計 |
| labor_imputed_days | 人時を埋めた日数 |
| other_cost | その他の経費（会計の店×月の「その他経費」） |
| operating_profit | 営業利益 ＝ gross_profit − labor_cost − other_cost |
| is_existing | 1 ＝ 既存店（その月の月初で開店から13か月以上、かつその月の末日まで営業。F246 と同じ） |

既存店の前年比は、FY2025 の各月で is_existing = 1 の店×月と、その前年同月（同じ店）を比べる（F246 の決めごと）。

## dim と、そのまま渡すもの
- `dim_store.csv`：store_id, store_name（架空）, area（都市・郊外・地方）, size（L・M・S）, open_date, close_date
- `dim_category.csv`：category_id 1〜7、category（部門名）と合成の設定値（margin・waste・promo。F246 の設定）
- `dim_date.csv`：date, ym, fy, dow（0＝月曜）, hol（祝日）, flyer（チラシの日）
- `dim_store_code_history.csv`：POS の店コード → store_id、有効期間（valid_from〜valid_to）、action（map＝店に置き換える、exclude＝除く）。補正表で足した2行（16店の新コード 1020、トレーニング用 9999）を含む
- `fact_member_month.csv`、`fact_ec_day.csv`：会員の月次とネットスーパーの日次。F246 のものをそのまま渡す（この回では整えていない）

## 正解との差（この mart の精度）
- 売上・客数・粗利・廃棄・部門の売上は、合成の正解（F246 のデータ）と円単位の丸めの差だけ（既存店売上 FY2025 で 7円）。
- 人時・人件費は、埋めた 460 店×日（全体の 1.4%）で正解と違う。埋めた日の人時の誤差は平均 2.9%。既存店の人時売上は −0.008%、営業利益の前年比は −0.02pt ずれる。

## 届いたファイル（data/raw_synth/）の列
| ファイル | 列 |
|---|---|
| pos_store_day.csv.gz | 店コード, 営業日, レシート枚数, 会員レシート枚数, 点数, 売上金額, 送信日時 |
| pos_dept_day.csv.gz | 店コード, 営業日, 部門コード, 売上金額, 粗利金額, 送信日時 |
| hr_attendance.csv.gz | 勤怠店番, 勤務日, 人時, 人件費 |
| waste_register.csv.gz | 店コード, 登録日, 部門コード, 廃棄金額 |
| acct_store_month.csv | 店番, 年月, 売上高, その他経費 |
| map_store_pos.csv | 店コード, 有効開始, 有効終了, 店番 |
| map_store_hr.csv | 勤怠店番, 店番 |
| map_dept.csv | 部門コード, 有効開始, 有効終了, 部門番号 |

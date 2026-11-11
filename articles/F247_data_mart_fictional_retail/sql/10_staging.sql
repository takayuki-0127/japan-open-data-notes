-- 10 staging：届いたファイルを「1行＝1つの事実」にそろえる（サンプルマート（架空）、合成データ）
-- SQL Server 互換の書き方（CTE・ROW_NUMBER・CASE・COALESCE・BETWEEN だけを使う）。この記事では DuckDB で実行した。
-- 入力テーブル（03_整える.py が CSV から作る。列名は届いたファイルのまま）
--   raw_pos_store_day, raw_pos_dept_day, raw_hr_attendance, raw_waste_register, raw_acct_store_month
--   map_store_pos, map_store_hr, map_dept           ：情報システム部・人事から受け取った対応表
--   ref_fix_store_code, ref_fix_waste_unit           ：分析担当がテストの結果を見て足した補正表
--   run_param(cutoff)                                ：この時点までに届いた分だけを使う（月次の締めの再現）

-- 店コードの対応（受け取った対応表＋補正表）
CREATE TABLE stg_store_code AS
SELECT "店コード" AS pos_code, "有効開始" AS valid_from, "有効終了" AS valid_to, "店番" AS store_id, 'map' AS action
FROM map_store_pos
UNION ALL
SELECT "店コード", "有効開始", "有効終了", "店番", "処理"
FROM ref_fix_store_code;

-- POS 店×日：締めの時点までに届いた行 → 再送を除く（同じ店コード×営業日の最新の送信だけ）→ 有効期間で店番に置き換え
CREATE TABLE stg_pos_store AS
WITH arrived AS (
    SELECT p.*
    FROM raw_pos_store_day AS p
    WHERE p."送信日時" <= (SELECT cutoff FROM run_param)
),
ranked AS (
    SELECT a.*,
           ROW_NUMBER() OVER (PARTITION BY a."店コード", a."営業日" ORDER BY a."送信日時" DESC) AS rn,
           COUNT(*)     OVER (PARTITION BY a."店コード", a."営業日") AS n_sent
    FROM arrived AS a
)
SELECT r."営業日" AS biz_date, c.store_id, r."店コード" AS pos_code,
       r."レシート枚数" AS receipts, r."会員レシート枚数" AS member_receipts, r."点数" AS items,
       r."売上金額" AS sales, r."送信日時" AS sent_at, r.n_sent
FROM ranked AS r
JOIN stg_store_code AS c
  ON c.pos_code = r."店コード" AND r."営業日" BETWEEN c.valid_from AND c.valid_to
WHERE r.rn = 1 AND c.action = 'map';

-- 対応表で店番にできなかった POS の行（テスト T02 で数える。捨てずに残す）
CREATE TABLE q_pos_unmapped AS
SELECT p."店コード" AS pos_code, p."営業日" AS biz_date, p."売上金額" AS sales
FROM raw_pos_store_day AS p
LEFT JOIN stg_store_code AS c
  ON c.pos_code = p."店コード" AND p."営業日" BETWEEN c.valid_from AND c.valid_to
WHERE c.pos_code IS NULL;

-- 部門コードの対応（2025-04 の付け替え・惣菜の分割は、対応表の有効期間で元の7部門に戻す）
CREATE TABLE stg_dept_code AS
SELECT "部門コード" AS dept_code, "有効開始" AS valid_from, "有効終了" AS valid_to, "部門番号" AS category_id
FROM map_dept;

-- POS 店×日×部門
CREATE TABLE stg_pos_dept AS
WITH arrived AS (
    SELECT d.* FROM raw_pos_dept_day AS d WHERE d."送信日時" <= (SELECT cutoff FROM run_param)
),
ranked AS (
    SELECT a.*, ROW_NUMBER() OVER (PARTITION BY a."店コード", a."営業日", a."部門コード" ORDER BY a."送信日時" DESC) AS rn
    FROM arrived AS a
)
SELECT r."営業日" AS biz_date, c.store_id, k.category_id, r."部門コード" AS dept_code,
       r."売上金額" AS sales, r."粗利金額" AS gross_profit_before_waste
FROM ranked AS r
JOIN stg_store_code AS c ON c.pos_code = r."店コード" AND r."営業日" BETWEEN c.valid_from AND c.valid_to AND c.action = 'map'
JOIN stg_dept_code  AS k ON k.dept_code = r."部門コード" AND r."営業日" BETWEEN k.valid_from AND k.valid_to
WHERE r.rn = 1;

-- 廃棄登録：店番・部門番号に置き換え、単位の補正（千円で入力された期間は ×1000）
CREATE TABLE stg_waste AS
SELECT w."登録日" AS biz_date, c.store_id, k.category_id,
       w."廃棄金額" * COALESCE(f."倍率", 1) AS waste,
       CASE WHEN f."倍率" IS NULL THEN 0 ELSE 1 END AS unit_fixed
FROM raw_waste_register AS w
JOIN stg_store_code AS c ON c.pos_code = w."店コード" AND w."登録日" BETWEEN c.valid_from AND c.valid_to AND c.action = 'map'
JOIN stg_dept_code  AS k ON k.dept_code = w."部門コード" AND w."登録日" BETWEEN k.valid_from AND k.valid_to
LEFT JOIN ref_fix_waste_unit AS f ON f."店番" = c.store_id AND w."登録日" BETWEEN f."開始" AND f."終了";

-- 勤怠：店番に置き換え。人時・人件費が空の日は、同じ店・同じ月・同じ曜日の平均で埋め、印をつける
CREATE TABLE stg_hr AS
WITH h AS (
    SELECT a."勤務日" AS biz_date, m."店番" AS store_id, d.ym, d.dow,
           a."人時" AS labor_hours, a."人件費" AS labor_cost
    FROM raw_hr_attendance AS a
    JOIN map_store_hr AS m ON m."勤怠店番" = a."勤怠店番"
    JOIN dim_date     AS d ON d."date" = a."勤務日"
),
fill AS (
    SELECT store_id, ym, dow, AVG(labor_hours) AS avg_hours
    FROM h WHERE labor_hours IS NOT NULL GROUP BY store_id, ym, dow
),
wage AS (
    SELECT store_id, ym, SUM(labor_cost) * 1.0 / SUM(labor_hours) AS wage
    FROM h WHERE labor_hours IS NOT NULL GROUP BY store_id, ym
)
SELECT h.biz_date, h.store_id,
       COALESCE(h.labor_hours, f.avg_hours) AS labor_hours,
       COALESCE(h.labor_cost, f.avg_hours * w.wage) AS labor_cost,
       CASE WHEN h.labor_hours IS NULL THEN 1 ELSE 0 END AS labor_imputed
FROM h
LEFT JOIN fill AS f ON f.store_id = h.store_id AND f.ym = h.ym AND f.dow = h.dow
LEFT JOIN wage AS w ON w.store_id = h.store_id AND w.ym = h.ym;

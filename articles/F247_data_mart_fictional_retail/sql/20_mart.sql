-- 20 mart：分析・レポート・ダッシュボードが使う形（サンプルマート（架空）、合成データ）
-- SQL Server 互換の書き方。この記事では DuckDB で実行した。
-- 粒度：店×日（mart_fact_store_day）、店×日×部門（mart_fact_store_day_dept）、店×月（mart_store_month）

-- 店×日×部門：元の7部門にまとめる（2025-04 以降の「弁当・寿司」は惣菜に足す）
CREATE TABLE mart_fact_store_day_dept AS
WITH s AS (
    SELECT biz_date, store_id, category_id,
           SUM(sales) AS sales, SUM(gross_profit_before_waste) AS gross_profit_before_waste
    FROM stg_pos_dept
    GROUP BY biz_date, store_id, category_id
),
w AS (
    SELECT biz_date, store_id, category_id, SUM(waste) AS waste
    FROM stg_waste
    GROUP BY biz_date, store_id, category_id
)
SELECT s.biz_date, s.store_id, s.category_id, s.sales, s.gross_profit_before_waste,
       COALESCE(w.waste, 0) AS waste
FROM s
LEFT JOIN w ON w.biz_date = s.biz_date AND w.store_id = s.store_id AND w.category_id = s.category_id;

-- 店×日：売上・客数は POS の店×日、粗利と廃棄は部門の合計、人時・人件費は勤怠から
CREATE TABLE mart_fact_store_day AS
WITH g AS (
    SELECT biz_date, store_id,
           SUM(gross_profit_before_waste) AS gross_profit_before_waste, SUM(waste) AS waste, SUM(sales) AS dept_sales
    FROM mart_fact_store_day_dept
    GROUP BY biz_date, store_id
)
SELECT p.biz_date, p.store_id, p.receipts, p.member_receipts, p.items, p.sales,
       g.gross_profit_before_waste, g.waste, g.gross_profit_before_waste - g.waste AS gross_profit,
       h.labor_hours, h.labor_cost, COALESCE(h.labor_imputed, 0) AS labor_imputed,
       g.dept_sales
FROM stg_pos_store AS p
LEFT JOIN g      ON g.biz_date = p.biz_date AND g.store_id = p.store_id
LEFT JOIN stg_hr AS h ON h.biz_date = p.biz_date AND h.store_id = p.store_id;

-- 店×月：その他の経費は会計の月次から。既存店の印もここでつける
-- 既存店：その月の月初で開店から13か月以上、かつその月の末日まで営業している店（F246 の決めごと）
CREATE TABLE mart_store_month AS
WITH m AS (
    SELECT d.ym, d.fy, f.store_id,
           COUNT(*) AS days_with_sales,
           SUM(f.sales) AS sales, SUM(f.receipts) AS receipts, SUM(f.member_receipts) AS member_receipts,
           SUM(f.items) AS items, SUM(f.gross_profit_before_waste) AS gross_profit_before_waste,
           SUM(f.waste) AS waste, SUM(f.gross_profit) AS gross_profit,
           SUM(f.labor_hours) AS labor_hours, SUM(f.labor_cost) AS labor_cost, SUM(f.labor_imputed) AS labor_imputed_days
    FROM mart_fact_store_day AS f
    JOIN dim_date AS d ON d."date" = f.biz_date
    GROUP BY d.ym, d.fy, f.store_id
),
cal AS (
    SELECT ym, MIN("date") AS month_start, MAX("date") AS month_end,
           CAST(SUBSTRING(ym, 1, 4) AS INT) * 12 + CAST(SUBSTRING(ym, 6, 2) AS INT) AS month_no
    FROM dim_date GROUP BY ym
)
SELECT m.*, a."その他経費" AS other_cost,
       m.gross_profit - m.labor_cost - a."その他経費" AS operating_profit,
       CASE WHEN c.month_no - (YEAR(s.open_date) * 12 + MONTH(s.open_date)) >= 13
             AND (s.close_date IS NULL OR s.close_date >= c.month_end) THEN 1 ELSE 0 END AS is_existing
FROM m
JOIN cal AS c ON c.ym = m.ym
LEFT JOIN dim_store AS s ON s.store_id = m.store_id
LEFT JOIN raw_acct_store_month AS a ON a."店番" = m.store_id AND a."年月" = m.ym;

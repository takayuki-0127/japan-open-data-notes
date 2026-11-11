-- サンプルマート（架空）：月次 KPI と既存店の前年同月比（SQL Server 互換の書き方。DuckDB でも動く）
-- 入力：dim_store, dim_date, fact_store_day（data/ の CSV と同じ列）
-- 既存店：その月の月初で開店から13か月以上、かつその月の末日まで営業している店。前年同月も同じ店で比べる。

WITH dim_month AS (
    SELECT ym,
           MIN(CAST([date] AS DATE)) AS month_start,
           MAX(CAST([date] AS DATE)) AS month_end,
           CAST(LEFT(ym, 4) AS INT) * 12 + CAST(RIGHT(ym, 2) AS INT) AS month_no
    FROM dim_date
    GROUP BY ym
),
store_month AS (
    SELECT d.ym,
           f.store_id,
           SUM(f.sales)            AS sales,
           SUM(f.receipts)         AS receipts,
           SUM(f.member_receipts)  AS member_receipts,
           SUM(f.items)            AS items,
           SUM(f.gross_profit)     AS gross_profit,
           SUM(f.waste)            AS waste,
           SUM(f.labor_hours)      AS labor_hours,
           SUM(f.labor_cost)       AS labor_cost,
           SUM(f.other_cost)       AS other_cost
    FROM fact_store_day AS f
    JOIN dim_date AS d ON d.[date] = f.[date]
    GROUP BY d.ym, f.store_id
),
existing AS (
    SELECT sm.ym, sm.store_id,
           CASE WHEN m.month_no - (YEAR(CAST(s.open_date AS DATE)) * 12 + MONTH(CAST(s.open_date AS DATE))) >= 13
                 AND (s.close_date IS NULL OR CAST(s.close_date AS DATE) >= m.month_end)
                THEN 1 ELSE 0 END AS is_existing
    FROM store_month AS sm
    JOIN dim_month AS m ON m.ym = sm.ym
    JOIN dim_store AS s ON s.store_id = sm.store_id
),
cur AS (
    SELECT sm.*, m.month_no
    FROM store_month AS sm
    JOIN existing AS e ON e.ym = sm.ym AND e.store_id = sm.store_id AND e.is_existing = 1
    JOIN dim_month AS m ON m.ym = sm.ym
),
pairs AS (
    SELECT c.ym, c.store_id,
           c.sales AS sales_1, p.sales AS sales_0,
           c.receipts AS receipts_1, p.receipts AS receipts_0,
           c.items AS items_1, p.items AS items_0,
           c.gross_profit AS gp_1, p.gross_profit AS gp_0,
           c.waste AS waste_1, p.waste AS waste_0,
           c.labor_hours AS lh_1, p.labor_hours AS lh_0
    FROM cur AS c
    JOIN dim_month AS pm ON pm.month_no = c.month_no - 12
    JOIN store_month AS p ON p.ym = pm.ym AND p.store_id = c.store_id
)
SELECT ym,
       COUNT(*)                                                              AS existing_stores,
       CAST(SUM(sales_1) AS FLOAT) / NULLIF(SUM(sales_0), 0) - 1             AS sales_yoy,
       CAST(SUM(receipts_1) AS FLOAT) / NULLIF(SUM(receipts_0), 0) - 1       AS receipts_yoy,
       (CAST(SUM(sales_1) AS FLOAT) / NULLIF(SUM(receipts_1), 0))
         / NULLIF(CAST(SUM(sales_0) AS FLOAT) / NULLIF(SUM(receipts_0), 0), 0) - 1 AS ticket_yoy,
       (CAST(SUM(items_1) AS FLOAT) / NULLIF(SUM(receipts_1), 0))
         / NULLIF(CAST(SUM(items_0) AS FLOAT) / NULLIF(SUM(receipts_0), 0), 0) - 1 AS items_per_receipt_yoy,
       CAST(SUM(gp_1) AS FLOAT) / NULLIF(SUM(sales_1), 0)
         - CAST(SUM(gp_0) AS FLOAT) / NULLIF(SUM(sales_0), 0)                  AS gp_rate_diff,
       CAST(SUM(waste_1) AS FLOAT) / NULLIF(SUM(sales_1), 0)
         - CAST(SUM(waste_0) AS FLOAT) / NULLIF(SUM(sales_0), 0)               AS waste_rate_diff,
       (CAST(SUM(gp_1) AS FLOAT) / NULLIF(SUM(lh_1), 0))
         / NULLIF(CAST(SUM(gp_0) AS FLOAT) / NULLIF(SUM(lh_0), 0), 0) - 1       AS gp_per_labor_hour_yoy
FROM pairs
GROUP BY ym
ORDER BY ym;

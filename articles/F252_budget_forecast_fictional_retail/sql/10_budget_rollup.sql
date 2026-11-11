-- 予算（店×月）を地域・年・月に積み上げる。SQL Server 互換の書き方（DuckDB で実行して確認。SQL Server では動かしていない）
-- 入力：budget_store_month(store_id, area, ym, sales, receipts, gross_profit, labor_hours, labor_cost, other_cost, operating_profit)
WITH b AS (
    SELECT area, ym, sales, gross_profit, labor_cost, other_cost, operating_profit
    FROM budget_store_month
)
SELECT
    COALESCE(area, N'全社') AS area,
    SUM(sales)            AS sales,
    SUM(gross_profit)     AS gross_profit,
    SUM(labor_cost)       AS labor_cost,
    SUM(other_cost)       AS other_cost,
    SUM(operating_profit) AS operating_profit,
    CAST(SUM(operating_profit) AS FLOAT) / NULLIF(SUM(sales), 0) AS op_margin
FROM b
GROUP BY ROLLUP (area)
ORDER BY area;

-- T-SQL：未検証（SQL Server では動かしていない）
-- B カレンダー表 dbo.calendar_month(ym) と結合して、抜けた月を0で埋めてから LAG
WITH s AS (SELECT DISTINCT store_id FROM dbo.monthly),
cal AS (SELECT s.store_id, c.ym FROM s CROSS JOIN dbo.calendar_month c
        WHERE c.ym >= '2024-01-01' AND c.ym < '2026-01-01'),
f AS (SELECT c.store_id, c.ym, COALESCE(m.sales, 0) AS sales
      FROM cal c LEFT JOIN dbo.monthly m ON m.store_id = c.store_id AND m.ym = c.ym)
SELECT store_id, ym, sales,
       LAG(sales) OVER (PARTITION BY store_id ORDER BY ym) AS prev_sales
FROM f;
-- C 前の行が前月でない行
SELECT COUNT(*) AS rows_not_prev_month
FROM (SELECT ym, LAG(ym) OVER (PARTITION BY store_id ORDER BY ym) AS prev_ym FROM dbo.monthly) t
WHERE prev_ym IS NOT NULL AND DATEDIFF(MONTH, prev_ym, ym) <> 1;

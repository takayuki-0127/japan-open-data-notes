-- 売上0の月は行がない表で、LAG の前月比を出す（DuckDB 版）
-- monthly(store_id, ym DATE（月初）, sales)
-- A そのまま LAG（前の「行」と比べる）
SELECT store_id, ym, sales,
       LAG(ym)    OVER (PARTITION BY store_id ORDER BY ym) AS prev_ym,
       LAG(sales) OVER (PARTITION BY store_id ORDER BY ym) AS prev_sales
FROM monthly
ORDER BY store_id, ym;
-- B 店×月のカレンダーと結合して、抜けた月を0で埋めてから LAG
WITH cal AS (
  SELECT s.store_id, m.ym
  FROM (SELECT DISTINCT store_id FROM monthly) s
  CROSS JOIN (SELECT CAST(range AS DATE) AS ym FROM range(DATE '2024-01-01', DATE '2026-01-01', INTERVAL 1 MONTH)) m),
f AS (
  SELECT c.store_id, c.ym, COALESCE(m.sales, 0) AS sales
  FROM cal c LEFT JOIN monthly m ON m.store_id = c.store_id AND m.ym = c.ym)
SELECT store_id, ym, sales,
       LAG(sales) OVER (PARTITION BY store_id ORDER BY ym) AS prev_sales
FROM f
ORDER BY store_id, ym;
-- C 前の行が本当に前月かを確かめる（月の差が1でない行を数える）
SELECT COUNT(*) AS rows_not_prev_month
FROM (SELECT ym, LAG(ym) OVER (PARTITION BY store_id ORDER BY ym) AS prev_ym FROM monthly) t
WHERE prev_ym IS NOT NULL AND date_diff('month', prev_ym, ym) <> 1;

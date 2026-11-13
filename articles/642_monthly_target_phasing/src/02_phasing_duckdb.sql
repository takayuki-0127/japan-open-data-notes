-- DuckDB：3通りの月の目標と達成の判定
WITH ly AS (
  SELECT store_id, mon, sales * 1.0 / SUM(sales) OVER (PARTITION BY store_id) AS share_ly
  FROM monthly_sales WHERE yr = 2024
), avg3 AS (
  SELECT store_id, mon, AVG(share) AS share_3y FROM (
    SELECT store_id, yr, mon, sales * 1.0 / SUM(sales) OVER (PARTITION BY store_id, yr) AS share
    FROM monthly_sales WHERE yr BETWEEN 2022 AND 2024) GROUP BY store_id, mon
)
SELECT a.store_id, a.mon, a.sales,
       t.annual_target / 12.0           AS target_equal,
       t.annual_target * ly.share_ly    AS target_ly,
       t.annual_target * avg3.share_3y  AS target_3y
FROM monthly_sales a
JOIN annual_target t USING (store_id)
JOIN ly   ON ly.store_id = a.store_id AND ly.mon = a.mon
JOIN avg3 ON avg3.store_id = a.store_id AND avg3.mon = a.mon
WHERE a.yr = 2025
ORDER BY a.store_id, a.mon

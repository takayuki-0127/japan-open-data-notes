-- 初回購入から W 日以内に2回目を買った人の割合（リピート率）を初回の月ごとに出す（DuckDB 版）
-- purchases(customer_id, purchase_date DATE)、データの最終日は 2025-06-30
WITH r AS (
  SELECT customer_id, purchase_date,
         ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY purchase_date) AS k
  FROM purchases),
f AS (
  SELECT customer_id,
         MAX(CASE WHEN k = 1 THEN purchase_date END) AS first_date,
         MAX(CASE WHEN k = 2 THEN purchase_date END) AS second_date
  FROM r GROUP BY customer_id)
SELECT date_trunc('month', first_date) AS cohort,
       COUNT(*) AS customers,
       AVG(CASE WHEN second_date <= first_date + INTERVAL 30 DAY THEN 1.0 ELSE 0 END) AS rate30,
       AVG(CASE WHEN second_date <= first_date + INTERVAL 90 DAY THEN 1.0 ELSE 0 END) AS rate90,
       -- 月の最後の日から90日たっていない月は出さない（NULL）
       CASE WHEN MAX(last_day(first_date)) + INTERVAL 90 DAY <= DATE '2025-06-30'
            THEN AVG(CASE WHEN second_date <= first_date + INTERVAL 90 DAY THEN 1.0 ELSE 0 END) END AS rate90_complete
FROM f
GROUP BY cohort
ORDER BY cohort;

-- T-SQL：未検証（SQL Server では動かしていない）
WITH r AS (
  SELECT customer_id, purchase_date,
         ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY purchase_date) AS k
  FROM dbo.purchases),
f AS (
  SELECT customer_id,
         MAX(CASE WHEN k = 1 THEN purchase_date END) AS first_date,
         MAX(CASE WHEN k = 2 THEN purchase_date END) AS second_date
  FROM r GROUP BY customer_id)
SELECT DATEFROMPARTS(YEAR(first_date), MONTH(first_date), 1) AS cohort,
       COUNT(*) AS customers,
       AVG(CASE WHEN second_date <= DATEADD(day, 30, first_date) THEN 1.0 ELSE 0 END) AS rate30,
       AVG(CASE WHEN second_date <= DATEADD(day, 90, first_date) THEN 1.0 ELSE 0 END) AS rate90,
       CASE WHEN DATEADD(day, 90, MAX(EOMONTH(first_date))) <= '2025-06-30'
            THEN AVG(CASE WHEN second_date <= DATEADD(day, 90, first_date) THEN 1.0 ELSE 0 END) END AS rate90_complete
FROM f
GROUP BY DATEFROMPARTS(YEAR(first_date), MONTH(first_date), 1)
ORDER BY cohort;

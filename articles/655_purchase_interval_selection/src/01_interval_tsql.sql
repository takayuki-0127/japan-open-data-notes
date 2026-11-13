-- T-SQL：未検証（SQL Server では動かしていない）
WITH g AS (
  SELECT customer_id,
         DATEDIFF(DAY, LAG(bought_on) OVER (PARTITION BY customer_id ORDER BY bought_on), bought_on) AS gap
  FROM dbo.purchases)
SELECT AVG(CAST(gap AS float)) AS mean_gap_2plus, COUNT(DISTINCT customer_id) AS customers_2plus
FROM g WHERE gap IS NOT NULL;

SELECT SUM(CAST(DATEDIFF(DAY, c.registered_on, '2025-12-31') AS float))
       / (SELECT COUNT(*) FROM dbo.purchases) AS days_per_purchase
FROM dbo.customers AS c;

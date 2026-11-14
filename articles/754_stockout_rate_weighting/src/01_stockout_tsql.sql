-- T-SQL：未検証（SQL Server では動かしていない）
-- stockout は int（欠品なら1）。AVG(int) は整数になるので、1.0 を掛けてから平均する
SELECT i.store_id,
       AVG(i.stockout * 1.0) * 100                                       AS rate_sku_days,
       SUM(i.stockout * s.daily_rate) / SUM(s.daily_rate) * 100          AS rate_sales_weighted,
       COUNT(DISTINCT CASE WHEN i.stockout = 1 THEN i.sku END) * 100.0
         / COUNT(DISTINCT i.sku)                                         AS rate_any_sku
FROM dbo.inventory i
JOIN dbo.skus s ON s.sku = i.sku
GROUP BY i.store_id
ORDER BY i.store_id;

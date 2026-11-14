-- T-SQL：未検証（SQL Server では動かしていない）
-- 既存店＝前年の同じ月も、今年のその月も、まる1か月営業した店
WITH cur AS (SELECT * FROM dbo.monthly WHERE ym BETWEEN '2025-01' AND '2025-12'),
     prv AS (SELECT store_id, FORMAT(DATEADD(YEAR, 1, CAST(ym + '-01' AS date)), 'yyyy-MM') AS ym, sales, open_days, days_in_month
             FROM dbo.monthly WHERE ym BETWEEN '2024-01' AND '2024-12')
SELECT c.ym,
       SUM(c.sales) AS sales_all,
       SUM(CASE WHEN p.store_id IS NOT NULL AND c.open_days = c.days_in_month AND p.open_days = p.days_in_month THEN c.sales END) AS sales_same,
       SUM(CASE WHEN c.open_days = c.days_in_month AND p.open_days = p.days_in_month THEN p.sales END) AS sales_same_prev
FROM cur AS c LEFT JOIN prv AS p ON p.store_id = c.store_id AND p.ym = c.ym
GROUP BY c.ym
ORDER BY c.ym;
-- 全店の前年の合計は prv を ym ごとに別に合計する

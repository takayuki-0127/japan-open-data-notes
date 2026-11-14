-- T-SQL：未検証
-- 4月始まりの年度
SELECT CASE WHEN MONTH(ym) >= 4 THEN YEAR(ym) ELSE YEAR(ym) - 1 END AS fy, SUM(sales) AS sales, COUNT(*) AS months
FROM dbo.sales_monthly
GROUP BY CASE WHEN MONTH(ym) >= 4 THEN YEAR(ym) ELSE YEAR(ym) - 1 END;
-- 12か月の移動合計
SELECT ym, SUM(sales) OVER (ORDER BY ym ROWS BETWEEN 11 PRECEDING AND CURRENT ROW) AS sales_12m
FROM dbo.sales_monthly;

-- 暦年・4月始まりの年度・12か月の移動合計で、前年比を出す（DuckDB）
-- sales_monthly：ym（月の初日）・sales
CREATE OR REPLACE TABLE by_cal AS
SELECT year(ym) AS y, SUM(sales) AS sales, COUNT(*) AS months FROM sales_monthly GROUP BY 1;
CREATE OR REPLACE TABLE by_fy AS
SELECT CASE WHEN month(ym) >= 4 THEN year(ym) ELSE year(ym) - 1 END AS fy, SUM(sales) AS sales, COUNT(*) AS months
FROM sales_monthly GROUP BY 1;
CREATE OR REPLACE TABLE rolling AS
SELECT ym, SUM(sales) OVER (ORDER BY ym ROWS BETWEEN 11 PRECEDING AND CURRENT ROW) AS sales_12m,
       COUNT(*)   OVER (ORDER BY ym ROWS BETWEEN 11 PRECEDING AND CURRENT ROW) AS months
FROM sales_monthly;
SELECT 1;

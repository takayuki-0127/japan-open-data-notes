-- T-SQL：未検証（SQL Server では動かしていない）
WITH m AS (
    SELECT YEAR(sales_date) AS y, MONTH(sales_date) AS mo,
           SUM(sales) AS total, COUNT(*) AS days,
           SUM(CASE WHEN MONTH(sales_date) = 2 AND DAY(sales_date) = 29 THEN 0 ELSE sales END) AS total_ex29
    FROM daily_sales
    GROUP BY YEAR(sales_date), MONTH(sales_date)
)
SELECT c.y, c.mo,
       c.total * 1.0 / p.total - 1                                   AS yoy_plain,
       (c.total * 1.0 / c.days) / (p.total * 1.0 / p.days) - 1       AS yoy_per_day,
       c.total_ex29 * 1.0 / p.total_ex29 - 1                         AS yoy_ex29
FROM m c JOIN m p ON p.y = c.y - 1 AND p.mo = c.mo
ORDER BY c.y, c.mo;

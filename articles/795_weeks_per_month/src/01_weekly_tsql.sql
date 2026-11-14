-- T-SQL：未検証
SELECT FORMAT(sale_date, 'yyyy-MM')                         AS ym,
       COUNT(*)                                             AS days,
       SUM(sales)                                           AS month_sales,
       SUM(sales) / 4.0                                     AS per_week_div4,
       SUM(sales) / (52.0 / 12)                             AS per_week_div433,
       SUM(sales) / (COUNT(*) / 7.0)                        AS per_week_days
FROM dbo.daily_sales
GROUP BY FORMAT(sale_date, 'yyyy-MM')
ORDER BY ym;

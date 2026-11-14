-- T-SQL：未検証（SQL Server では動かしていない）
SELECT DATEFROMPARTS(YEAR(sale_date), MONTH(sale_date), 1)            AS ym,
       SUM(sales)                                                      AS month_sales,
       SUM(sales) / 30.0                                               AS per_day_30,
       SUM(sales) * 1.0 / DAY(EOMONTH(MIN(sale_date)))                 AS per_day_calendar,
       SUM(sales) * 1.0 / COUNT(DISTINCT sale_date)                    AS per_day_business,
       COUNT(DISTINCT sale_date)                                       AS business_days
FROM dbo.daily
GROUP BY DATEFROMPARTS(YEAR(sale_date), MONTH(sale_date), 1)
ORDER BY ym;

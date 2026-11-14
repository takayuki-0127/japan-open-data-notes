-- 月の売上を「30」「暦の日数」「営業日数」で割って日あたりを出す（DuckDB 版）
-- daily(sale_date DATE, sales)：営業した日だけ行がある
SELECT date_trunc('month', sale_date)                    AS ym,
       SUM(sales)                                         AS month_sales,
       SUM(sales) / 30.0                                  AS per_day_30,
       SUM(sales) / day(last_day(MIN(sale_date)))         AS per_day_calendar,
       SUM(sales) / COUNT(DISTINCT sale_date)             AS per_day_business,
       COUNT(DISTINCT sale_date)                          AS business_days
FROM daily
GROUP BY ym
ORDER BY ym;

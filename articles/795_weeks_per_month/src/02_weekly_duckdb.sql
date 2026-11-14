-- 月の売上を「週あたり」に直す3通り（DuckDB）
SELECT strftime(sale_date, '%Y-%m')                        AS ym,
       COUNT(*)                                             AS days,
       SUM(sales)                                           AS month_sales,
       SUM(sales) / 4.0                                     AS per_week_div4,      -- 4で割る
       SUM(sales) / (52.0 / 12)                             AS per_week_div433,    -- 4.33（52÷12）で割る
       SUM(sales) / (COUNT(*) / 7.0)                        AS per_week_days       -- その月の日数÷7で割る
FROM daily_sales
GROUP BY ym
ORDER BY ym;

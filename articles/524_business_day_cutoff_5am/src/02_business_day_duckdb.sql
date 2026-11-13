-- 朝5時締めの営業日で日ごとの売上を出す（DuckDB で実行）
-- sales(hour_start TIMESTAMP, sales)：1時間ごとの売上
SELECT CAST(hour_start - INTERVAL 5 HOUR AS DATE) AS business_date,
       SUM(sales)                                AS sales
FROM sales
GROUP BY business_date
ORDER BY business_date;

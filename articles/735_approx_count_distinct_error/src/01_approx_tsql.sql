-- T-SQL：未検証
-- APPROX_COUNT_DISTINCT は SQL Server 2019 以降の関数。誤差の大きさは DuckDB と同じとは限らない
SELECT segment,
       COUNT(*)                       AS n_rows,
       COUNT(DISTINCT user_id)        AS exact_users,
       APPROX_COUNT_DISTINCT(user_id) AS approx_users
FROM dbo.access_log
GROUP BY segment
ORDER BY segment;

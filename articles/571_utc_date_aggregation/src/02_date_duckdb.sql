-- UTC で保存した注文時刻を、日本時間の日付と UTC のままの日付で数える（DuckDB）
WITH jst AS (
  SELECT CAST(ordered_at_utc + INTERVAL 9 HOUR AS DATE) AS d, COUNT(*) AS n_jst
  FROM orders GROUP BY 1
), utc AS (
  SELECT CAST(ordered_at_utc AS DATE) AS d, COUNT(*) AS n_utc   -- 日本時間に直していない
  FROM orders GROUP BY 1
)
SELECT COALESCE(jst.d, utc.d) AS d, COALESCE(n_jst, 0) AS n_jst, COALESCE(n_utc, 0) AS n_utc
FROM jst FULL OUTER JOIN utc ON jst.d = utc.d
ORDER BY d;

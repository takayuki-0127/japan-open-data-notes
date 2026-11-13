-- T-SQL：未検証
WITH t AS (
  SELECT t.*, MAX(t.seq) OVER (PARTITION BY t.user_id) AS n
  FROM dbo.touches t JOIN dbo.users u ON u.user_id = t.user_id
  WHERE u.converted = 1
)
SELECT channel,
       SUM(CASE WHEN seq = n THEN 1 ELSE 0 END) AS last_touch,
       SUM(1.0 / n)                             AS linear
FROM t GROUP BY channel ORDER BY channel;

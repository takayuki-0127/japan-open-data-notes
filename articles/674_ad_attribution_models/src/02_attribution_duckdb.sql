-- 申し込んだ人の接点に、最後の接点と均等で成果を付ける（DuckDB）
WITH t AS (
  SELECT t.*, MAX(seq) OVER (PARTITION BY t.user_id) AS n
  FROM touches t JOIN users u USING (user_id)
  WHERE u.converted = 1
)
SELECT channel,
       SUM(CASE WHEN seq = n THEN 1 ELSE 0 END) AS last_touch,
       SUM(1.0 / n)                             AS linear
FROM t GROUP BY channel ORDER BY channel;

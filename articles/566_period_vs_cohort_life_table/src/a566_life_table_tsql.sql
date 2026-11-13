-- 期間生命表（T-SQL 版。SQL Server では動かしていない：未検証）
-- 入力 dbo.qx_table(age INT, qx FLOAT)
WITH s AS (
  SELECT age, qx,
         EXP(COALESCE(SUM(LOG(CASE WHEN 1 - qx > 1e-300 THEN 1 - qx ELSE 1e-300 END))
             OVER (ORDER BY age ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING), 0)) AS lx
  FROM dbo.qx_table
), t AS (
  SELECT age, qx, lx, lx * (1 - qx) AS lx_next FROM s
)
SELECT age, qx, lx,
       SUM(lx_next) OVER (ORDER BY age ROWS BETWEEN CURRENT ROW AND UNBOUNDED FOLLOWING) / lx + 0.5 AS ex
FROM t
ORDER BY age;

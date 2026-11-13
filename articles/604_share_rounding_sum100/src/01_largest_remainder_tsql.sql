-- T-SQL：未検証（SQL Server では動かしていない）
WITH s AS (
  SELECT table_id, item, value,
         100.0 * value / SUM(value) OVER (PARTITION BY table_id) AS pct
  FROM dbo.shares),
f AS (
  SELECT *, FLOOR(pct) AS base, pct - FLOOR(pct) AS rem,
         100 - SUM(FLOOR(pct)) OVER (PARTITION BY table_id) AS short
  FROM s),
r AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY table_id ORDER BY rem DESC, item) AS rk
  FROM f)
SELECT table_id, item, pct,
       ROUND(pct, 0) AS pct_round,
       base + CASE WHEN rk <= short THEN 1 ELSE 0 END AS pct_lr
FROM r
ORDER BY table_id, item;

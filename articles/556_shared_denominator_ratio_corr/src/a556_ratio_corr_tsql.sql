-- T-SQL 版（SQL Server では動かしていない：未検証）
-- SQL Server には CORR がないので、相関を和から計算する
WITH r AS (
  SELECT CAST(inquiries AS float)                          AS x,
         CAST(returns   AS float)                          AS y,
         CAST(inquiries AS float) / NULLIF(visitors, 0)    AS a,
         CAST(returns   AS float) / NULLIF(visitors, 0)    AS b
  FROM dbo.stores)
SELECT (COUNT(*) * SUM(x * y) - SUM(x) * SUM(y))
       / SQRT((COUNT(*) * SUM(x * x) - SUM(x) * SUM(x)) * (COUNT(*) * SUM(y * y) - SUM(y) * SUM(y))) AS r_raw,
       (COUNT(*) * SUM(a * b) - SUM(a) * SUM(b))
       / SQRT((COUNT(*) * SUM(a * a) - SUM(a) * SUM(a)) * (COUNT(*) * SUM(b * b) - SUM(b) * SUM(b))) AS r_ratio,
       COUNT(*) AS n_stores
FROM r;

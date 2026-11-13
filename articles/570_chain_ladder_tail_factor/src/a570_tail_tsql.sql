-- 進展係数と ln(係数−1) の直線の当てはめ（T-SQL 版。SQL Server では動かしていない：未検証）
-- 入力 dbo.tri(ay INT, dev INT, paid FLOAT)
WITH pair AS (
  SELECT a.dev, SUM(b.paid) / SUM(a.paid) AS ldf
  FROM dbo.tri AS a JOIN dbo.tri AS b ON b.ay = a.ay AND b.dev = a.dev + 1
  GROUP BY a.dev
), p AS (
  SELECT CAST(dev AS FLOAT) AS x, LOG(ldf - 1) AS y FROM pair WHERE dev >= 3 AND ldf > 1
)
SELECT (COUNT(*) * SUM(x * y) - SUM(x) * SUM(y)) / (COUNT(*) * SUM(x * x) - SUM(x) * SUM(x)) AS slope,
       (SUM(y) - (COUNT(*) * SUM(x * y) - SUM(x) * SUM(y)) / (COUNT(*) * SUM(x * x) - SUM(x) * SUM(x)) * SUM(x)) / COUNT(*) AS intercept,
       COUNT(*) AS n_points
FROM p;

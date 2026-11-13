-- 出来高で重み付けた進展係数（T-SQL 版。SQL Server では動かしていない：未検証）
-- 入力 dbo.tri(ay INT, dev INT, incurred FLOAT)
WITH pair AS (
  SELECT a.dev, a.incurred AS now_amt, b.incurred AS next_amt
  FROM dbo.tri AS a
  JOIN dbo.tri AS b ON b.ay = a.ay AND b.dev = a.dev + 1
)
SELECT dev, SUM(next_amt) / SUM(now_amt) AS ldf, COUNT(*) AS n_ay
FROM pair
GROUP BY dev
ORDER BY dev;

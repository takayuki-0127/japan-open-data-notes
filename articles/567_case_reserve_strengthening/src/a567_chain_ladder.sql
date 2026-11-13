-- 発生ベースの三角形（縦持ち：ay, dev, incurred）から、出来高で重み付けた進展係数を出す（DuckDB）
-- dev の列から dev+1 の列への係数 = 両方そろう事故年の dev+1 の合計 / dev の合計
WITH pair AS (
  SELECT a.dev, a.incurred AS now_amt, b.incurred AS next_amt
  FROM tri a
  JOIN tri b ON b.ay = a.ay AND b.dev = a.dev + 1
)
SELECT dev, SUM(next_amt) / SUM(now_amt) AS ldf, COUNT(*) AS n_ay
FROM pair
GROUP BY dev
ORDER BY dev;

-- 支払の三角形（縦持ち：ay, dev, paid）から進展係数を出し、
-- 3年目以降の ln(係数−1) を経過年数に直線で当てはめる（指数の外挿、DuckDB）
WITH pair AS (
  SELECT a.dev, SUM(b.paid) / SUM(a.paid) AS ldf
  FROM tri a JOIN tri b ON b.ay = a.ay AND b.dev = a.dev + 1
  GROUP BY a.dev
)
SELECT REGR_SLOPE(LN(ldf - 1), dev)     AS slope,
       REGR_INTERCEPT(LN(ldf - 1), dev) AS intercept,
       COUNT(*)                         AS n_points
FROM pair
WHERE dev >= 3 AND ldf > 1;

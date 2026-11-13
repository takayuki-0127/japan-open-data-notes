-- DuckDB：単純な比較と、前の購入額の十分位でそろえた比較
WITH d AS (
  SELECT *, NTILE(10) OVER (ORDER BY prev_spend, customer_id) AS dec10 FROM customers
), s AS (
  SELECT dec10,
         AVG(CASE WHEN used = 1 THEN next_spend END) - AVG(CASE WHEN used = 0 THEN next_spend END) AS diff,
         SUM(used) AS n_used
  FROM d GROUP BY dec10
)
SELECT (SELECT AVG(next_spend) FILTER (WHERE used = 1) - AVG(next_spend) FILTER (WHERE used = 0) FROM customers) AS naive_diff,
       SUM(diff * n_used) / SUM(n_used) AS adjusted_diff
FROM s

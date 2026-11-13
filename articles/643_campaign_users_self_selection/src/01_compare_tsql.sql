-- T-SQL：未検証（SQL Server では動かしていない）
-- 使った人と使わなかった人を、前の購入額の十分位の中で比べてから平均する
WITH d AS (
  SELECT *, NTILE(10) OVER (ORDER BY prev_spend, customer_id) AS dec10 FROM dbo.customers
), s AS (
  SELECT dec10,
         AVG(CASE WHEN used = 1 THEN next_spend * 1.0 END) - AVG(CASE WHEN used = 0 THEN next_spend * 1.0 END) AS diff,
         SUM(used) AS n_used
  FROM d GROUP BY dec10
)
SELECT SUM(diff * n_used) * 1.0 / SUM(n_used) AS adjusted_diff FROM s;

-- 桁のずれた行の候補を出す（T-SQL、SQL Server では未検証）
WITH s AS (
  SELECT dept, month, amount,
         LAG(amount) OVER (PARTITION BY dept ORDER BY month) AS prev,
         PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY amount)
           OVER (PARTITION BY dept)                          AS med
  FROM dbo.dept_monthly)
SELECT dept, month, amount,
       CASE WHEN amount <= prev / 100.0 THEN 1 ELSE 0 END AS m1,
       CASE WHEN amount <= med  / 100.0 THEN 1 ELSE 0 END AS m2
FROM s
ORDER BY dept, month;

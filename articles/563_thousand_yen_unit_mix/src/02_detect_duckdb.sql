-- 桁のずれた行の候補を出す（DuckDB）
-- m1 前月比：前月の1/100以下 ／ m2 中央値との倍率：部門の中央値の1/100以下
WITH s AS (
  SELECT dept, month, amount,
         LAG(amount) OVER (PARTITION BY dept ORDER BY month) AS prev,
         MEDIAN(amount) OVER (PARTITION BY dept)             AS med
  FROM dept_monthly)
SELECT dept, month, amount,
       amount <= prev / 100.0 AS m1,
       amount <= med  / 100.0 AS m2
FROM s
ORDER BY dept, month;

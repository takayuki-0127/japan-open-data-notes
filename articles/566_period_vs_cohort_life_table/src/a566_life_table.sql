-- 期間生命表：各年齢の死亡率 qx から、生存数 lx と平均余命 ex を出す（DuckDB）
-- 入力 qx_table(age, qx)。lx は 1 から始め、各年の途中で亡くなる人は半年生きたとみなす
WITH s AS (
  SELECT age, qx,
         EXP(COALESCE(SUM(LN(GREATEST(1 - qx, 1e-300))) OVER (ORDER BY age
             ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING), 0)) AS lx
  FROM qx_table
), t AS (
  SELECT age, qx, lx, lx * (1 - qx) AS lx_next FROM s
)
SELECT age, qx, lx,
       SUM(lx_next) OVER (ORDER BY age ROWS BETWEEN CURRENT ROW AND UNBOUNDED FOLLOWING) / lx + 0.5 AS ex
FROM t
ORDER BY age;

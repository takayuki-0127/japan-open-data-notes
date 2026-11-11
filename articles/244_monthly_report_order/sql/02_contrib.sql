-- 02 予算との差を部門に分け、寄与の大きい順に並べる（T-SQL と DuckDB で同じ文。DuckDB で検証）
WITH m AS (
    SELECT ym, dept, actual, budget,
           actual - budget                                  AS diff,
           SUM(actual - budget) OVER (PARTITION BY ym)      AS diff_total,
           CAST(actual AS FLOAT) / NULLIF(budget, 0) - 1    AS rate
    FROM dbo.monthly_dept
)
SELECT ym, dept, actual, budget, diff, diff_total, rate,
       RANK() OVER (PARTITION BY ym ORDER BY ABS(diff) DESC) AS rank_by_amount,
       RANK() OVER (PARTITION BY ym ORDER BY ABS(rate) DESC) AS rank_by_rate
FROM m
ORDER BY ym, rank_by_amount;

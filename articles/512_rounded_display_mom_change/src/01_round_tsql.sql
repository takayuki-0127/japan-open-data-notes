-- T-SQL 版（SQL Server では動かしていない：未検証）
-- 表示どうしの差と、丸める前の差を丸めた値を並べ、食い違う月を数える
WITH m AS (
    SELECT kpi, ym, rate,
           LAG(rate) OVER (PARTITION BY kpi ORDER BY ym) AS prev
    FROM dbo.kpi_monthly
)
SELECT kpi,
       SUM(CASE WHEN ROUND(rate, 1) = ROUND(prev, 1) THEN 1 ELSE 0 END)                     AS shown_zero,
       SUM(CASE WHEN SIGN(ROUND(rate, 1) - ROUND(prev, 1)) * SIGN(rate - prev) < 0 THEN 1 ELSE 0 END) AS shown_reversed,
       SUM(CASE WHEN ROUND(rate, 1) - ROUND(prev, 1) <> ROUND(rate - prev, 1) THEN 1 ELSE 0 END) AS mismatch
FROM m
WHERE prev IS NOT NULL
GROUP BY kpi;

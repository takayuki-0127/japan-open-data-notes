-- T-SQL 版（SQL Server では動かしていない：未検証）
-- 整数どうしの割り算は小数が切り捨てられるので、1.0 を掛けてから割る
WITH y AS (
    SELECT 1 AS [year], store, visitors_y1 AS visitors, buyers_y1 AS buyers FROM dbo.stores
    UNION ALL
    SELECT 2, store, visitors_y2, buyers_y2 FROM dbo.stores
)
SELECT [year],
       AVG(buyers * 1.0 / visitors)                              AS simple_mean,
       SUM(buyers) * 1.0 / SUM(visitors)                          AS ratio_of_totals
FROM y
GROUP BY [year]
ORDER BY [year];

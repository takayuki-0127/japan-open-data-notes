-- T-SQL 版（SQL Server では動かしていない：未検証）
WITH t AS (
    SELECT lower, upper, n,
           SUM(n) OVER (ORDER BY lower ROWS UNBOUNDED PRECEDING) AS cum,
           SUM(n) OVER ()                                         AS total
    FROM dbo.freq
)
SELECT TOP (1) lower + (total / 2.0 - (cum - n)) / CAST(n AS float) * (upper - lower) AS median_interp
FROM t
WHERE cum >= total / 2.0
ORDER BY lower;

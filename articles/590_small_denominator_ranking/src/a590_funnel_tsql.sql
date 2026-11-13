-- T-SQL 版（SQL Server では動かしていない：未検証）
WITH overall AS (
    SELECT SUM(buyers) * 1.0 / SUM(visitors) AS p FROM dbo.stores
)
SELECT s.store, s.visitors, s.buyers,
       s.buyers * 1.0 / s.visitors AS rate,
       o.p - 1.96 * SQRT(o.p * (1 - o.p) / s.visitors) AS lower_limit,
       o.p + 1.96 * SQRT(o.p * (1 - o.p) / s.visitors) AS upper_limit,
       CASE WHEN ABS(s.buyers * 1.0 / s.visitors - o.p) > 1.96 * SQRT(o.p * (1 - o.p) / s.visitors)
            THEN 1 ELSE 0 END AS outside
FROM dbo.stores AS s CROSS JOIN overall AS o
ORDER BY rate DESC;

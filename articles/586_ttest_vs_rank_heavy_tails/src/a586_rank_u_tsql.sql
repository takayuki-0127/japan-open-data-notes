-- T-SQL 版（SQL Server では動かしていない：未検証）
WITH r AS (
    SELECT grp, value, AVG(CAST(rk AS float)) OVER (PARTITION BY value) AS rank_avg
    FROM (SELECT grp, value, ROW_NUMBER() OVER (ORDER BY value) AS rk FROM dbo.obs) AS t
)
SELECT SUM(rank_avg) - COUNT(*) * (COUNT(*) + 1) / 2.0 AS u_group_a
FROM r
WHERE grp = 'A';
-- p 値は、U の平均 n1*n2/2 と標準偏差 sqrt(n1*n2*(n1+n2+1)/12) から正規近似で出す

-- T-SQL 版（SQL Server では動かしていない：未検証）
WITH g AS (
    SELECT grp, COUNT(*) AS n, AVG(CAST(value AS float)) AS m, VAR(value) AS v
    FROM dbo.obs
    GROUP BY grp
), w AS (
    SELECT MAX(CASE WHEN grp = 'A' THEN n END) AS n1, MAX(CASE WHEN grp = 'A' THEN m END) AS m1, MAX(CASE WHEN grp = 'A' THEN v END) AS v1,
           MAX(CASE WHEN grp = 'B' THEN n END) AS n2, MAX(CASE WHEN grp = 'B' THEN m END) AS m2, MAX(CASE WHEN grp = 'B' THEN v END) AS v2
    FROM g
)
SELECT (m1 - m2) / SQRT(((n1 - 1) * v1 + (n2 - 1) * v2) / (n1 + n2 - 2) * (1.0 / n1 + 1.0 / n2)) AS t_student,
       (m1 - m2) / SQRT(v1 / n1 + v2 / n2) AS t_welch,
       POWER(v1 / n1 + v2 / n2, 2) / (POWER(v1 / n1, 2) / (n1 - 1) + POWER(v2 / n2, 2) / (n2 - 1)) AS df_welch
FROM w;
-- p 値は t 分布から求める。SQL Server には t 分布の関数がないため、Excel の T.DIST.2T などで計算する

-- 事故年・契約年度・報告年の3通りで、年ごとの事故率を出す（T-SQL、未検証：SQL Server では動かしていない）
-- 表 dbo.claims(start_month, accident_month, report_month, claims)、dbo.policies(start_month, policies)。月は 'YYYY-MM'
WITH k AS (SELECT value AS k FROM GENERATE_SERIES(0, 11)),        -- SQL Server 2022 以降
months AS (
    SELECT p.start_month, p.policies,
           FORMAT(DATEADD(month, k.k, CAST(p.start_month + '-01' AS date)), 'yyyy-MM') AS exp_month
    FROM dbo.policies AS p CROSS JOIN k
), earned AS (
    SELECT CAST(LEFT(exp_month, 4) AS int) AS year, SUM(policies / 12.0) AS exposure
    FROM months GROUP BY CAST(LEFT(exp_month, 4) AS int)
), acc AS (
    SELECT CAST(LEFT(accident_month, 4) AS int) AS year, SUM(claims) AS n FROM dbo.claims GROUP BY CAST(LEFT(accident_month, 4) AS int)
), rep AS (
    SELECT CAST(LEFT(report_month, 4) AS int) AS year, SUM(claims) AS n FROM dbo.claims GROUP BY CAST(LEFT(report_month, 4) AS int)
), polc AS (
    SELECT CAST(LEFT(start_month, 4) AS int) AS year, SUM(claims) AS n FROM dbo.claims GROUP BY CAST(LEFT(start_month, 4) AS int)
), pol AS (
    SELECT CAST(LEFT(start_month, 4) AS int) AS year, SUM(policies) AS policies FROM dbo.policies GROUP BY CAST(LEFT(start_month, 4) AS int)
)
SELECT e.year,
       acc.n * 1.0 / e.exposure    AS accident,
       polc.n * 1.0 / pol.policies AS policy,
       rep.n * 1.0 / e.exposure    AS report
FROM earned AS e
JOIN acc  ON acc.year = e.year
JOIN rep  ON rep.year = e.year
JOIN pol  ON pol.year = e.year
JOIN polc ON polc.year = e.year
WHERE e.year BETWEEN 2019 AND 2025
ORDER BY e.year;

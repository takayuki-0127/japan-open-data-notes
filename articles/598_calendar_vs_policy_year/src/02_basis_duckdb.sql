-- 事故年・契約年度・報告年の3通りで、年ごとの事故率を出す（DuckDB）
-- 表 claims(start_month, accident_month, report_month, claims)、policies(start_month, policies)。月は 'YYYY-MM'
WITH months AS (                                   -- 各契約の12か月に、件数の1/12ずつ経過分を割り振る
    SELECT p.start_month, p.policies,
           strftime(CAST(p.start_month || '-01' AS DATE) + INTERVAL (k) MONTH, '%Y-%m') AS exp_month
    FROM policies AS p CROSS JOIN range(12) AS t(k)
), earned AS (
    SELECT CAST(LEFT(exp_month, 4) AS INTEGER) AS year, SUM(policies / 12.0) AS exposure
    FROM months GROUP BY 1
), acc AS (
    SELECT CAST(LEFT(accident_month, 4) AS INTEGER) AS year, SUM(claims) AS n FROM claims GROUP BY 1
), rep AS (
    SELECT CAST(LEFT(report_month, 4) AS INTEGER) AS year, SUM(claims) AS n FROM claims GROUP BY 1
), polc AS (
    SELECT CAST(LEFT(start_month, 4) AS INTEGER) AS year, SUM(claims) AS n FROM claims GROUP BY 1
), pol AS (
    SELECT CAST(LEFT(start_month, 4) AS INTEGER) AS year, SUM(policies) AS policies FROM policies GROUP BY 1
)
SELECT e.year,
       acc.n * 1.0 / e.exposure  AS accident,     -- 事故年：その年に起きた事故 ÷ その年の経過件数
       polc.n * 1.0 / pol.policies AS policy,     -- 契約年度：その年に始まった契約の事故 ÷ その年に始まった契約の件数
       rep.n * 1.0 / e.exposure  AS report        -- 報告年：その年に報告された事故 ÷ その年の経過件数
FROM earned AS e JOIN acc USING (year) JOIN rep USING (year) JOIN pol USING (year) JOIN polc USING (year)
WHERE e.year BETWEEN 2019 AND 2025
ORDER BY e.year;

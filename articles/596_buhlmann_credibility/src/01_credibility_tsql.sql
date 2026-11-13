-- Bühlmann–Straub のクレジビリティ（T-SQL、未検証：SQL Server では動かしていない）
-- 表 dbo.claims_by_year(group_id, year, policies, claims)
WITH g AS (
    SELECT group_id, CAST(SUM(policies) AS float) AS w_i,
           CAST(SUM(claims) AS float) / SUM(policies) AS x_i, COUNT(*) AS n_years
    FROM dbo.claims_by_year GROUP BY group_id
), tot AS (
    SELECT SUM(w_i) AS w, SUM(w_i * x_i) / SUM(w_i) AS xbar, SUM(w_i * w_i) AS w2,
           COUNT(*) AS n_groups, SUM(n_years - 1) AS dof
    FROM g
), s2 AS (
    SELECT SUM(c.policies * SQUARE(CAST(c.claims AS float) / c.policies - g.x_i)) / MAX(t.dof) AS s2
    FROM dbo.claims_by_year AS c JOIN g ON g.group_id = c.group_id CROSS JOIN tot AS t
), a AS (
    SELECT (SUM(g.w_i * SQUARE(g.x_i - t.xbar)) - (MAX(t.n_groups) - 1) * MAX(s2.s2))
           / (MAX(t.w) - MAX(t.w2) / MAX(t.w)) AS a_raw
    FROM g CROSS JOIN tot AS t CROSS JOIN s2
), z AS (
    SELECT g.group_id, g.w_i, g.x_i,
           s2.s2 / IIF(a.a_raw > 1e-12, a.a_raw, 1e-12) AS k,
           g.w_i / (g.w_i + s2.s2 / IIF(a.a_raw > 1e-12, a.a_raw, 1e-12)) AS z
    FROM g CROSS JOIN s2 CROSS JOIN a
), mu AS (
    SELECT SUM(z * x_i) / SUM(z) AS mu FROM z
)
SELECT z.group_id, z.w_i AS policies_3y, z.x_i AS own_rate, z.k, z.z,
       z.z * z.x_i + (1 - z.z) * mu.mu AS credibility_rate
FROM z CROSS JOIN mu
ORDER BY z.group_id;

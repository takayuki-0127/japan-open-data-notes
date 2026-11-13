-- Bühlmann–Straub のクレジビリティ（DuckDB）。表 claims_by_year(group_id, year, policies, claims)
WITH g AS (                                  -- 群ごとの合計の件数と、件数で重み付けた事故率
    SELECT group_id, SUM(policies) AS w_i, SUM(claims) * 1.0 / SUM(policies) AS x_i, COUNT(*) AS n_years
    FROM claims_by_year GROUP BY group_id
), tot AS (
    SELECT SUM(w_i) AS w, SUM(w_i * x_i) / SUM(w_i) AS xbar, SUM(w_i * w_i) AS w2,
           COUNT(*) AS n_groups, SUM(n_years - 1) AS dof
    FROM g
), s2 AS (                                   -- 群の中の年ごとの揺れ
    SELECT SUM(c.policies * POWER(c.claims * 1.0 / c.policies - g.x_i, 2)) / MAX(t.dof) AS s2
    FROM claims_by_year AS c JOIN g USING (group_id) CROSS JOIN tot AS t
), a AS (                                    -- 群どうしの本当の差（負なら0に近い値）
    SELECT GREATEST((SUM(g.w_i * POWER(g.x_i - t.xbar, 2)) - (MAX(t.n_groups) - 1) * MAX(s2.s2))
                    / (MAX(t.w) - MAX(t.w2) / MAX(t.w)), 1e-12) AS a
    FROM g CROSS JOIN tot AS t CROSS JOIN s2
), z AS (
    SELECT g.group_id, g.w_i, g.x_i, s2.s2 / a.a AS k, g.w_i / (g.w_i + s2.s2 / a.a) AS z
    FROM g CROSS JOIN s2 CROSS JOIN a
), mu AS (                                   -- Z で重み付けた全体の平均
    SELECT SUM(z * x_i) / SUM(z) AS mu FROM z
)
SELECT z.group_id, z.w_i AS policies_3y, z.x_i AS own_rate, z.k, z.z,
       z.z * z.x_i + (1 - z.z) * mu.mu AS credibility_rate
FROM z CROSS JOIN mu
ORDER BY z.group_id;

-- 店ごとの購入率と、漏斗図の線（全体の率 ± 1.96 × 標準誤差）を出し、線の外に出た店に印を付ける（DuckDB）
WITH overall AS (
    SELECT SUM(buyers) * 1.0 / SUM(visitors) AS p FROM stores
)
SELECT s.store, s.visitors, s.buyers,
       s.buyers * 1.0 / s.visitors                                AS rate,
       o.p - 1.96 * SQRT(o.p * (1 - o.p) / s.visitors)            AS lower_limit,
       o.p + 1.96 * SQRT(o.p * (1 - o.p) / s.visitors)            AS upper_limit,
       CASE WHEN s.buyers * 1.0 / s.visitors > o.p + 1.96 * SQRT(o.p * (1 - o.p) / s.visitors)
              OR s.buyers * 1.0 / s.visitors < o.p - 1.96 * SQRT(o.p * (1 - o.p) / s.visitors)
            THEN 1 ELSE 0 END                                     AS outside
FROM stores AS s CROSS JOIN overall AS o
ORDER BY rate DESC;

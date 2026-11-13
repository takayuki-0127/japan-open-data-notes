-- 層ごとの率の差・率の比・オッズ比と、それぞれでの順位（DuckDB で実行）
WITH r AS (
    SELECT segment,
           MAX(CASE WHEN coupon = 1 THEN n_buyers * 1.0 / n_customers END) AS p1,
           MAX(CASE WHEN coupon = 0 THEN n_buyers * 1.0 / n_customers END) AS p0
    FROM counts
    GROUP BY segment
), m AS (
    SELECT segment, p0, p1,
           p1 - p0                                  AS rate_diff,
           p1 / p0                                  AS rate_ratio,
           (p1 / (1 - p1)) / (p0 / (1 - p0))        AS odds_ratio
    FROM r
)
SELECT *,
       RANK() OVER (ORDER BY rate_diff DESC)  AS rank_diff,
       RANK() OVER (ORDER BY rate_ratio DESC) AS rank_ratio,
       RANK() OVER (ORDER BY odds_ratio DESC) AS rank_odds
FROM m
ORDER BY segment;

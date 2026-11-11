-- 04 集計.sql：A/B テストの結果を SQL で集計する（SQL Server 互換の書き方）
-- テーブル ab_events(user_id INT, arm VARCHAR(1), converted INT, spend FLOAT)
-- arm は 'A'（対照）と 'B'（処置）。データは架空のECサイトを想定したシミュレーション
WITH by_arm AS (
    SELECT arm,
           COUNT(*)                         AS n,
           SUM(converted)                   AS conv,
           CAST(SUM(converted) AS FLOAT) / COUNT(*) AS rate,
           AVG(spend)                       AS mean_spend
    FROM ab_events
    GROUP BY arm
), pooled AS (
    SELECT CAST(SUM(conv) AS FLOAT) / SUM(n) AS p_pool FROM by_arm
)
SELECT a.n AS n_a, b.n AS n_b, a.rate AS rate_a, b.rate AS rate_b,
       b.rate - a.rate                                   AS diff,
       (b.rate - a.rate) / a.rate                        AS rel_lift,
       (b.rate - a.rate) / SQRT(p.p_pool * (1 - p.p_pool) * (1.0 / a.n + 1.0 / b.n)) AS z_stat,
       b.mean_spend / a.mean_spend - 1                   AS rel_lift_spend
FROM by_arm a CROSS JOIN by_arm b CROSS JOIN pooled p
WHERE a.arm = 'A' AND b.arm = 'B';

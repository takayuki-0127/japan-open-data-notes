-- 04 CUPED の集計（SQL Server 互換の書き方。DuckDB でも動く）
-- 入力テーブル sim_users(user_id, arm, pre_visits, visits)
-- 出力：群ごとの素の平均・調整後の平均、差・標準誤差・z（素の差と CUPED）
WITH base AS (
    SELECT arm,
           CAST(pre_visits AS FLOAT) AS x,
           CAST(visits AS FLOAT) AS y
    FROM sim_users
),
m AS (   -- 全体の平均（両群まとめて）
    SELECT AVG(x) AS mx, AVG(y) AS my, COUNT(*) AS n FROM base
),
th AS (  -- θ = cov(y, x) / var(x)（両群まとめて推定）
    SELECT SUM((b.y - m.my) * (b.x - m.mx)) / SUM((b.x - m.mx) * (b.x - m.mx)) AS theta
    FROM base b CROSS JOIN m
),
adj AS ( -- 調整後の値 y - θ (x - mean(x))
    SELECT b.arm, b.y, b.y - th.theta * (b.x - m.mx) AS ya
    FROM base b CROSS JOIN m CROSS JOIN th
),
g AS (   -- 群ごとの平均と分散（標本分散）
    SELECT arm, COUNT(*) AS n,
           AVG(y) AS mean_y, AVG(ya) AS mean_ya,
           SUM(y * y) AS syy, SUM(ya * ya) AS saa
    FROM adj GROUP BY arm
),
g2 AS (
    SELECT arm, n, mean_y, mean_ya,
           (syy - n * mean_y * mean_y) / (n - 1) AS var_y,
           (saa - n * mean_ya * mean_ya) / (n - 1) AS var_ya
    FROM g
)
SELECT 'naive' AS method,
       b.mean_y - a.mean_y AS est,
       SQRT(b.var_y / b.n + a.var_y / a.n) AS se,
       (b.mean_y - a.mean_y) / SQRT(b.var_y / b.n + a.var_y / a.n) AS z
FROM g2 a JOIN g2 b ON a.arm = 'A' AND b.arm = 'B'
UNION ALL
SELECT 'cuped',
       b.mean_ya - a.mean_ya,
       SQRT(b.var_ya / b.n + a.var_ya / a.n),
       (b.mean_ya - a.mean_ya) / SQRT(b.var_ya / b.n + a.var_ya / a.n)
FROM g2 a JOIN g2 b ON a.arm = 'A' AND b.arm = 'B';

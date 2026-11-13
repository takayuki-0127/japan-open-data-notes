-- 割り付けの比の確認（SRM、DuckDB 版）。assignments(user_id, arm, day, converted)。予定は A:B = 50:50
-- 実際の人数と予定の人数から、カイ二乗の統計量（自由度1）を出す
WITH c AS (
  SELECT COUNT(*) FILTER (WHERE arm = 'A') AS n_a,
         COUNT(*) FILTER (WHERE arm = 'B') AS n_b,
         COUNT(*) AS n
  FROM assignments
)
SELECT n_a, n_b, n,
       n_b * 1.0 / n AS share_b,
       POWER(n_a - n * 0.5, 2) / (n * 0.5) + POWER(n_b - n * 0.5, 2) / (n * 0.5) AS chi2
FROM c;

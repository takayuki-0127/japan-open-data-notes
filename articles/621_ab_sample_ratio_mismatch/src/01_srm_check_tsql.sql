-- T-SQL：未検証（SQL Server では動かしていない）
-- 割り付けの比の確認（SRM）。dbo.assignments(user_id, arm, day, converted)。予定は A:B = 50:50
WITH c AS (
  SELECT SUM(CASE WHEN arm = 'A' THEN 1 ELSE 0 END) AS n_a,
         SUM(CASE WHEN arm = 'B' THEN 1 ELSE 0 END) AS n_b,
         COUNT(*) AS n
  FROM dbo.assignments
)
SELECT n_a, n_b, n,
       CAST(n_b AS float) / n AS share_b,
       POWER(n_a - n * 0.5, 2) / (n * 0.5) + POWER(n_b - n * 0.5, 2) / (n * 0.5) AS chi2
FROM c;
-- p 値は SQL Server に関数がないので、chi2 が 10.83 を超えたら p<0.001 と読む（自由度1）

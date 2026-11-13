-- T-SQL：未検証
WITH resp AS (
  SELECT age_group, COUNT(*) * 1.0 / SUM(COUNT(*)) OVER () AS resp_share
  FROM dbo.survey GROUP BY age_group
), w AS (
  SELECT s.*, p.pop_share / r.resp_share AS wt
  FROM dbo.survey s JOIN resp r ON r.age_group = s.age_group JOIN dbo.pop p ON p.age_group = s.age_group
)
SELECT AVG(CAST(satisfied AS float))             AS unweighted,
       SUM(wt * satisfied) / SUM(wt)             AS weighted,
       SUM(wt) * SUM(wt) / SUM(wt * wt)          AS effective_n
FROM w;

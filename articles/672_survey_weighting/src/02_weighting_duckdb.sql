-- 年代の重み付きの満足の割合（DuckDB）
WITH resp AS (
  SELECT age_group, COUNT(*) * 1.0 / SUM(COUNT(*)) OVER () AS resp_share
  FROM survey GROUP BY age_group
), w AS (
  SELECT s.*, p.pop_share / r.resp_share AS wt
  FROM survey s JOIN resp r USING (age_group) JOIN pop p USING (age_group)
)
SELECT AVG(satisfied::DOUBLE)                    AS unweighted,
       SUM(wt * satisfied) / SUM(wt)             AS weighted,
       SUM(wt) * SUM(wt) / SUM(wt * wt)          AS effective_n
FROM w;

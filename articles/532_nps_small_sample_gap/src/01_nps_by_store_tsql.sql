-- 店別の NPS と、その幅の目安（T-SQL 版、SQL Server では未検証）
-- dbo.resp(n_per_store, store, score)
WITH s AS (
  SELECT n_per_store, store, COUNT(*) AS n,
         AVG(CASE WHEN score >= 9 THEN 1.0 ELSE 0.0 END) AS p_pro,
         AVG(CASE WHEN score <= 6 THEN 1.0 ELSE 0.0 END) AS p_det
  FROM dbo.resp
  GROUP BY n_per_store, store)
SELECT n_per_store, store, n,
       100.0 * (p_pro - p_det) AS nps,
       -- NPS の標準誤差（ポイント）：sqrt((p+ + p- - (p+ - p-)^2) / n)
       100.0 * SQRT((p_pro + p_det - SQUARE(p_pro - p_det)) / n) AS se_pt
FROM s
ORDER BY n_per_store, store;

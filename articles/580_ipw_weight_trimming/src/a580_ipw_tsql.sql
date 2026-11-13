-- T-SQL 版（SQL Server では動かしていない：未検証）
WITH w AS (
    SELECT *, CASE WHEN treated = 1 THEN 1.0 / ps ELSE 1.0 / (1 - ps) END AS wt
    FROM dbo.units
)
SELECT
    SUM(CASE WHEN treated = 1 THEN wt * y END) / SUM(CASE WHEN treated = 1 THEN wt END)
  - SUM(CASE WHEN treated = 0 THEN wt * y END) / SUM(CASE WHEN treated = 0 THEN wt END) AS ipw,
    MAX(wt) AS max_weight,
    SUM(wt) * SUM(wt) / SUM(wt * wt) AS effective_n
FROM w;
-- 傾向スコアそのものは、ロジスティック回帰などで別に推定してから表に入れる

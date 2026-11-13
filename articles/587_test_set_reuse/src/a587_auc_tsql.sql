-- T-SQL 版（SQL Server では動かしていない：未検証）
WITH r AS (
    SELECT y, AVG(CAST(rk AS float)) OVER (PARTITION BY score) AS rank_avg
    FROM (SELECT y, score, ROW_NUMBER() OVER (ORDER BY score) AS rk FROM dbo.pred) AS t
)
SELECT (SUM(CASE WHEN y = 1 THEN rank_avg END)
        - SUM(y) * (SUM(y) + 1) / 2.0)
       / (SUM(y) * (COUNT(*) - SUM(y))) AS auc
FROM r;

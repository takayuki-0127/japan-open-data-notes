-- T-SQL 版（SQL Server では動かしていない：未検証）
WITH b AS (
    SELECT CASE WHEN FLOOR(pred * 10) > 9 THEN 9 ELSE CAST(FLOOR(pred * 10) AS int) END AS bin,
           pred, churned
    FROM dbo.predictions
)
SELECT bin,
       COUNT(*)                                       AS n_members,
       AVG(pred)                                      AS mean_pred,
       AVG(CAST(churned AS float))                    AS actual_rate,
       (SELECT AVG((pred - churned) * (pred - churned)) FROM dbo.predictions) AS brier
FROM b
GROUP BY bin
ORDER BY bin;

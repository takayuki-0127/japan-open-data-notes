-- T-SQL 版（SQL Server では動かしていない：未検証）
WITH g AS (
    SELECT treated,
           AVG(CAST(sales_before AS float))                AS m0,
           AVG(CAST(sales_after AS float))                 AS m1,
           AVG(CAST(sales_after - sales_before AS float))  AS mchg
    FROM dbo.stores GROUP BY treated
), w AS (
    SELECT SUM((s.sales_before - g.m0) * (s.sales_after - g.m1))  AS sxy,
           SUM((s.sales_before - g.m0) * (s.sales_before - g.m0)) AS sxx
    FROM dbo.stores AS s JOIN g ON g.treated = s.treated
), t AS (
    SELECT MAX(CASE WHEN treated = 1 THEN m0 END) - MAX(CASE WHEN treated = 0 THEN m0 END)     AS pre_gap,
           MAX(CASE WHEN treated = 1 THEN m1 END) - MAX(CASE WHEN treated = 0 THEN m1 END)     AS post_gap,
           MAX(CASE WHEN treated = 1 THEN mchg END) - MAX(CASE WHEN treated = 0 THEN mchg END) AS change_score_diff
    FROM g
)
SELECT t.change_score_diff,
       w.sxy / w.sxx                            AS pooled_slope,
       t.post_gap - (w.sxy / w.sxx) * t.pre_gap AS ancova_effect
FROM t CROSS JOIN w;

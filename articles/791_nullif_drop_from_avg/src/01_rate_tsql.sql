-- T-SQL：未検証
SELECT store_id,
       COUNT(*)                                                       AS days,
       COUNT(applications * 1.0 / NULLIF(visits, 0))                 AS days_used,
       AVG(applications * 1.0 / NULLIF(visits, 0))                   AS avg_daily_nullif,
       AVG(COALESCE(applications * 1.0 / NULLIF(visits, 0), 0))      AS avg_daily_zero,
       SUM(applications) * 1.0 / NULLIF(SUM(visits), 0)              AS rate_total
FROM dbo.daily
GROUP BY store_id
ORDER BY store_id;

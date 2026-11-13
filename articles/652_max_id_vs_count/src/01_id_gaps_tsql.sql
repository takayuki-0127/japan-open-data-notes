-- T-SQL：未検証（SQL Server では動かしていない）
SELECT FORMAT(created_at, 'yyyy-MM')     AS ym,
       COUNT(*)                          AS n_rows,
       MAX(app_id) - MIN(app_id) + 1     AS n_by_id_range,
       MAX(app_id)                       AS max_id
FROM dbo.applications
GROUP BY FORMAT(created_at, 'yyyy-MM')
ORDER BY ym;

SELECT app_id, prev_id, app_id - prev_id - 1 AS missing
FROM (SELECT app_id, LAG(app_id) OVER (ORDER BY app_id) AS prev_id FROM dbo.applications) AS t
WHERE app_id - prev_id > 1
ORDER BY missing DESC;

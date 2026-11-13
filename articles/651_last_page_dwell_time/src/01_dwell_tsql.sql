-- T-SQL：未検証（SQL Server では動かしていない）
SELECT session_id, seq, page, ts,
       DATEDIFF(SECOND, ts, LEAD(ts) OVER (PARTITION BY session_id ORDER BY seq)) AS dwell_sec
INTO #dwell
FROM dbo.pageviews;

SELECT page,
       AVG(CAST(dwell_sec AS float))               AS avg_drop_last,
       AVG(CAST(COALESCE(dwell_sec, 0) AS float))  AS avg_last_as_zero,
       COUNT(*) AS views,
       SUM(CASE WHEN dwell_sec IS NULL THEN 1 ELSE 0 END) AS exits
FROM #dwell
GROUP BY page
ORDER BY page;

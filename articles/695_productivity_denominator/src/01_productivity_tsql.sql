-- T-SQL：未検証（SQL Server では動かしていない）
SELECT staff_id,
       SUM(cases) * 1.0 / COUNT(DISTINCT work_date)      AS cases_per_day,
       SUM(cases) * 1.0 / SUM(hours)                     AS cases_per_hour,
       SUM(cases * difficulty) * 1.0 / SUM(hours)        AS weighted_per_hour
FROM daily_work
GROUP BY staff_id;

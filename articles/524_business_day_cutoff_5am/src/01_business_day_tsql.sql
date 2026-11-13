-- T-SQL 版（SQL Server では動かしていない：未検証）
-- dbo.sales(hour_start datetime2, sales int)：1時間ごとの売上。朝5時締めの営業日と暦日で日ごとに集計し、曜日別に平均する
WITH d AS (
    SELECT CAST(DATEADD(HOUR, -5, hour_start) AS date) AS business_date,
           CAST(hour_start AS date)                    AS calendar_date,
           sales
    FROM dbo.sales
),
bus AS (SELECT business_date AS dt, SUM(sales) AS sales FROM d GROUP BY business_date),
cal AS (SELECT calendar_date AS dt, SUM(sales) AS sales FROM d GROUP BY calendar_date)
SELECT DATENAME(WEEKDAY, b.dt) AS weekday_name,
       AVG(CAST(c.sales AS float)) AS calendar_avg,
       AVG(CAST(b.sales AS float)) AS business_avg
FROM bus AS b
LEFT JOIN cal AS c ON c.dt = b.dt
WHERE b.dt BETWEEN '2025-01-01' AND '2025-12-31'
GROUP BY DATENAME(WEEKDAY, b.dt), DATEPART(WEEKDAY, b.dt)
ORDER BY DATEPART(WEEKDAY, b.dt);

-- T-SQL 版（SQL Server では動かしていない：未検証）
-- dbo.inv([date] date, inbound float, shipped float, inv_end float)：日ごとの入荷・払出し・日末の在庫
DECLARE @y0 date = '2025-01-01', @y1 date = '2025-12-31';
WITH y AS (SELECT * FROM dbo.inv WHERE [date] BETWEEN @y0 AND @y1),
     per_day AS (SELECT SUM(shipped) / COUNT(*) AS v FROM y),
     opening AS (SELECT inv_end AS v FROM dbo.inv WHERE [date] = DATEADD(DAY, -1, @y0)),
     closing AS (SELECT inv_end AS v FROM y WHERE [date] = @y1),
     month_end AS (SELECT inv_end AS v FROM y WHERE [date] = EOMONTH([date])
                   UNION ALL SELECT v FROM opening)
SELECT ((SELECT v FROM opening) + (SELECT v FROM closing)) / 2 / (SELECT v FROM per_day) AS days_open_close,
       (SELECT AVG(v) FROM month_end) / (SELECT v FROM per_day)                          AS days_month_end,
       (SELECT AVG(inv_end) FROM y) / (SELECT v FROM per_day)                            AS days_daily;

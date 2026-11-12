-- 週の予測誤差と管理限界（T-SQL。SQL Server 本体では試していない＝未検証。DuckDB 版は 01_weekly_error_chart_duckdb.sql）
WITH wk AS (
    SELECT DATEADD(day, -(DATEDIFF(day, '2023-01-02', d.sales_date) % 7), d.sales_date) AS week_start,
           SUM(d.actual) AS actual, SUM(d.forecast) AS forecast
    FROM dbo.daily_demand AS d GROUP BY DATEADD(day, -(DATEDIFF(day, '2023-01-02', d.sales_date) % 7), d.sales_date)
), err AS (
    SELECT week_start, CAST(actual - forecast AS FLOAT) / forecast AS bias FROM wk
), lim AS (   -- 管理限界は「決めた期間」だけで計算して固定する
    SELECT AVG(bias) AS mu, STDEV(bias) AS sd FROM err WHERE week_start BETWEEN '2024-01-01' AND '2024-06-24'
)
SELECT e.week_start, e.bias, (e.bias - l.mu) / l.sd AS z,
       CASE WHEN ABS((e.bias - l.mu) / l.sd) > 3 THEN 1 ELSE 0 END AS r1_3sigma,
       CASE WHEN SUM(CASE WHEN (e.bias - l.mu) / l.sd > 1 THEN 1 ELSE 0 END)
                 OVER (ORDER BY e.week_start ROWS BETWEEN 3 PRECEDING AND CURRENT ROW) = 4 THEN 1 ELSE 0 END AS r3_4weeks_up
FROM err AS e CROSS JOIN lim AS l
ORDER BY e.week_start;

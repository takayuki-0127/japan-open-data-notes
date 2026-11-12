-- DuckDB で実際に動かした版（T-SQL 版との違い：日付の関数と STDEV → stddev_samp）
WITH wk AS (
    SELECT sales_date - CAST(date_diff('day', DATE '2023-01-02', sales_date) % 7 AS INTEGER) AS week_start,
           SUM(actual) AS actual, SUM(forecast) AS forecast
    FROM daily_demand GROUP BY 1
), err AS (
    SELECT week_start, CAST(actual - forecast AS DOUBLE) / forecast AS bias FROM wk
), lim AS (
    SELECT AVG(bias) AS mu, stddev_samp(bias) AS sd FROM err WHERE week_start BETWEEN DATE '2024-01-01' AND DATE '2024-06-24'
)
SELECT e.week_start, e.bias, (e.bias - l.mu) / l.sd AS z,
       CASE WHEN ABS((e.bias - l.mu) / l.sd) > 3 THEN 1 ELSE 0 END AS r1_3sigma,
       CASE WHEN SUM(CASE WHEN (e.bias - l.mu) / l.sd > 1 THEN 1 ELSE 0 END)
                 OVER (ORDER BY e.week_start ROWS BETWEEN 3 PRECEDING AND CURRENT ROW) = 4 THEN 1 ELSE 0 END AS r3_4weeks_up
FROM err AS e CROSS JOIN lim AS l
ORDER BY e.week_start;

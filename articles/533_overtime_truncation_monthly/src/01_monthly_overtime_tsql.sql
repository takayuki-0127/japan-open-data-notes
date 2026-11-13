-- 日ごとの残業（18:00より後の分）を4通りに丸めてから、人ごとに月の合計を出す（T-SQL 版、SQL Server では未検証）
-- dbo.att(emp, work_date, clock_in 'HH:MM', clock_out 'HH:MM')
WITH d AS (
  SELECT emp, work_date,
         CASE WHEN DATEDIFF(minute, CAST('00:00' AS time), CAST(clock_out AS time)) > 1080
              THEN DATEDIFF(minute, CAST('00:00' AS time), CAST(clock_out AS time)) - 1080 ELSE 0 END AS ot
  FROM dbo.att)
SELECT emp,
       SUM(ot)                    AS m1,
       SUM(ot / 15 * 15)          AS t15,   -- 整数どうしの割り算は切り捨て
       SUM(ot / 30 * 30)          AS t30,
       SUM((ot + 7) / 15 * 15)    AS r15
FROM d
GROUP BY emp
ORDER BY emp;

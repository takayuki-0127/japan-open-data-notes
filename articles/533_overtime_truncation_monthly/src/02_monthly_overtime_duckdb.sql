-- 日ごとの残業（18:00より後の分）を4通りに丸めてから、人ごとに月の合計を出す（DuckDB で実行）
-- att(emp, work_date, clock_in 'HH:MM', clock_out 'HH:MM')
WITH d AS (
  SELECT emp, work_date,
         GREATEST(CAST(split_part(clock_out, ':', 1) AS INTEGER) * 60
                + CAST(split_part(clock_out, ':', 2) AS INTEGER) - 1080, 0) AS ot
  FROM att)
SELECT emp,
       SUM(ot)                       AS m1,    -- 1分単位
       SUM(ot // 15 * 15)            AS t15,   -- 15分切り捨て
       SUM(ot // 30 * 30)            AS t30,   -- 30分切り捨て
       SUM((ot + 7) // 15 * 15)      AS r15    -- 15分の四捨五入（8分以上は切り上げ）
FROM d
GROUP BY emp
ORDER BY emp;

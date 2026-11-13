-- 勤務を日付ごとに分けて、日ごとの時間を出す（DuckDB）
-- 1回の勤務は24時間未満とする。開始日の0時から翌日の0時までと、翌日の0時以降の2つに分ける
WITH parts AS (
  SELECT shift_id, CAST(start_at AS DATE) AS work_date,
         date_diff('minute', start_at, LEAST(end_at, CAST(start_at AS DATE) + INTERVAL 1 DAY)) AS minutes
  FROM shifts
  UNION ALL
  SELECT shift_id, CAST(start_at AS DATE) + 1,
         date_diff('minute', CAST(start_at AS DATE) + INTERVAL 1 DAY, end_at)
  FROM shifts
  WHERE end_at > CAST(start_at AS DATE) + INTERVAL 1 DAY
)
SELECT work_date, SUM(minutes) / 60.0 AS hours_split
FROM parts
GROUP BY work_date
ORDER BY work_date;

-- 比べる方：開始日に全部つける
-- SELECT CAST(start_at AS DATE) AS work_date, SUM(date_diff('minute', start_at, end_at)) / 60.0 FROM shifts GROUP BY 1;

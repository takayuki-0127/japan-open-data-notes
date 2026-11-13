-- 勤務を日付ごとに分けて、日ごとの時間を出す（T-SQL、未検証）
SELECT p.work_date, SUM(p.minutes) / 60.0 AS hours_split
FROM dbo.shifts AS s
CROSS APPLY (VALUES
  (CAST(s.start_at AS date),
   DATEDIFF(minute, s.start_at,
     CASE WHEN s.end_at < DATEADD(day, 1, CAST(CAST(s.start_at AS date) AS datetime2))
          THEN s.end_at ELSE DATEADD(day, 1, CAST(CAST(s.start_at AS date) AS datetime2)) END)),
  (DATEADD(day, 1, CAST(s.start_at AS date)),
   CASE WHEN s.end_at > DATEADD(day, 1, CAST(CAST(s.start_at AS date) AS datetime2))
        THEN DATEDIFF(minute, DATEADD(day, 1, CAST(CAST(s.start_at AS date) AS datetime2)), s.end_at) ELSE 0 END)
) AS p(work_date, minutes)
WHERE p.minutes > 0
GROUP BY p.work_date
ORDER BY p.work_date;

-- 時刻だけ（開始 22:00、終了 06:00）で持っている表では、終了が開始より前なら翌日とみなす
-- CASE WHEN end_time < start_time THEN DATEDIFF(minute, start_time, end_time) + 1440
--      ELSE DATEDIFF(minute, start_time, end_time) END

-- T-SQL：未検証
SELECT DATEPART(hour, CAST(recv_time AS time))                           AS hour_ok,      -- '12:30 AM' は 0時として読まれるはず（未検証）
       CAST(LEFT(recv_time, CHARINDEX(':', recv_time) - 1) AS int)
         + CASE WHEN recv_time LIKE '%PM' THEN 12 ELSE 0 END             AS hour_naive,
       CAST(LEFT(recv_time, CHARINDEX(':', recv_time) - 1) AS int)      AS hour_no_ampm,
       COUNT(*) AS n
FROM dbo.logs
GROUP BY DATEPART(hour, CAST(recv_time AS time)),
         CAST(LEFT(recv_time, CHARINDEX(':', recv_time) - 1) AS int)
           + CASE WHEN recv_time LIKE '%PM' THEN 12 ELSE 0 END,
         CAST(LEFT(recv_time, CHARINDEX(':', recv_time) - 1) AS int)
ORDER BY hour_ok, hour_naive;

-- T-SQL 版（SQL Server では動かしていない：未検証）
-- ordered_at_utc は datetime2（UTC）。日本時間の日付に直してから数える
SELECT CAST(DATEADD(HOUR, 9, ordered_at_utc) AS date) AS d,
       COUNT(*) AS n, SUM(amount) AS amount
FROM dbo.orders
GROUP BY CAST(DATEADD(HOUR, 9, ordered_at_utc) AS date)
ORDER BY d;

-- タイムゾーン名で直す書き方（SQL Server 2016 以降）
SELECT CAST((ordered_at_utc AT TIME ZONE 'UTC') AT TIME ZONE 'Tokyo Standard Time' AS date) AS d,
       COUNT(*) AS n
FROM dbo.orders
GROUP BY CAST((ordered_at_utc AT TIME ZONE 'UTC') AT TIME ZONE 'Tokyo Standard Time' AS date);

-- 期間で絞るときも、日本時間の境目を UTC に直して比べる（2025年11月の日本時間）
SELECT COUNT(*) AS n
FROM dbo.orders
WHERE ordered_at_utc >= '2025-10-31T15:00:00' AND ordered_at_utc < '2025-11-30T15:00:00';

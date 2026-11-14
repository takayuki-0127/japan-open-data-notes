-- T-SQL：未検証（SQL Server では動かしていない）
-- ordered_at は datetime2。日付に直すなら CAST(... AS date)
SELECT CAST(ordered_at AS date) AS d, COUNT(*) AS orders, SUM(amount) AS amount
FROM dbo.orders
GROUP BY CAST(ordered_at AS date)
ORDER BY d;
-- 文字にするなら CONVERT の 120 形式の先頭10桁（yyyy-mm-dd）
SELECT CONVERT(char(10), ordered_at, 120) AS d, COUNT(*) AS orders
FROM dbo.orders
GROUP BY CONVERT(char(10), ordered_at, 120);
-- カレンダー表と結ぶなら、= ではなく期間で結ぶ
SELECT c.d, COUNT(o.order_id) AS orders
FROM dbo.calendar c
LEFT JOIN dbo.orders o ON o.ordered_at >= c.d AND o.ordered_at < DATEADD(day, 1, c.d)
GROUP BY c.d
ORDER BY c.d;

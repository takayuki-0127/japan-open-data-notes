-- T-SQL 版（SQL Server では動かしていない：未検証）
-- 日次の締めの在庫：d日目までに起きて、締め時刻（d日目の翌日0時＋@lag_hours）までに記録された入出庫を積み上げる
DECLARE @lag_hours int = 9;

SELECT c.item_id, c.stock_date,
       s.init_qty + COALESCE(SUM(m.qty), 0) AS stock_at_cutoff
FROM dbo.calendar_items AS c                      -- 品目×日付の表
JOIN dbo.init_stock    AS s ON s.item_id = c.item_id
LEFT JOIN dbo.movements AS m                      -- 入庫は＋、出庫は−の数量
       ON m.item_id = c.item_id
      AND m.event_at  <  DATEADD(day, 1, CAST(c.stock_date AS datetime2))
      AND m.record_at <= DATEADD(hour, @lag_hours, DATEADD(day, 1, CAST(c.stock_date AS datetime2)))
GROUP BY c.item_id, c.stock_date, s.init_qty;

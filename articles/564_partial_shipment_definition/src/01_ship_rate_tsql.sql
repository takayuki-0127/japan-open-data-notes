DECLARE @month_start date = '2025-10-01', @asof date = '2025-10-31';
-- 月末（:asof）時点で、その月（:month_start〜:asof）に受けた注文の出荷率を3つの定義で出す（T-SQL、SQL Server では未検証）
WITH o AS (
  SELECT o.order_id, SUM(l.qty) AS order_qty
  FROM dbo.orders o JOIN dbo.order_lines l USING (order_id)
  WHERE o.order_date BETWEEN @month_start AND @asof
  GROUP BY o.order_id),
s AS (
  SELECT order_id, SUM(ship_qty) AS shipped
  FROM dbo.shipments
  WHERE ship_date <= @asof
  GROUP BY order_id),
r AS (
  SELECT o.order_id, COALESCE(s.shipped, 0) AS shipped, o.order_qty
  FROM o LEFT JOIN s USING (order_id))
SELECT COUNT(*)                                             AS orders,
       AVG(CASE WHEN shipped > 0 THEN 1 ELSE 0 END)         AS s1_any,    -- 1回でも出荷
       AVG(CASE WHEN shipped >= order_qty THEN 1 ELSE 0 END) AS s2_full,  -- 全量出荷
       AVG(shipped * 1.0 / order_qty)                       AS s3_ratio   -- 数量の比
FROM r;

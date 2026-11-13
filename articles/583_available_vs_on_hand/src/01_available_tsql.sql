-- 日ごとの引当可能数 = 有り高 − 未出荷の受注残（T-SQL、未検証）
SELECT
  s.snap_date,
  s.sku,
  s.on_hand,
  COALESCE(SUM(o.qty), 0)             AS reserved_qty,
  s.on_hand - COALESCE(SUM(o.qty), 0) AS available_qty,
  CASE WHEN s.on_hand <= 0 THEN 1 ELSE 0 END                         AS out_by_book,
  CASE WHEN s.on_hand - COALESCE(SUM(o.qty), 0) <= 0 THEN 1 ELSE 0 END AS out_by_available
FROM dbo.stock_snapshot AS s
LEFT JOIN dbo.orders AS o
  ON o.sku = s.sku
 AND o.ordered_on <= s.snap_date
 AND (o.shipped_on IS NULL OR o.shipped_on > s.snap_date)
GROUP BY s.snap_date, s.sku, s.on_hand
ORDER BY s.snap_date, s.sku;

-- 日ごとの引当可能数 = 有り高 − 未出荷の受注残（DuckDB）
-- stock_snapshot：snap_date・sku・on_hand（その日の終わりの帳簿の在庫）
-- orders：order_id・sku・ordered_on・qty・due_on・shipped_on（未出荷は空）
SELECT
  s.snap_date,
  s.sku,
  s.on_hand,
  COALESCE(SUM(o.qty), 0)              AS reserved_sql,     -- その日までに受けて、まだ出していない数量
  s.on_hand - COALESCE(SUM(o.qty), 0)  AS available_sql
FROM stock_snapshot s
LEFT JOIN orders o
  ON o.sku = s.sku
 AND o.ordered_on <= s.snap_date
 AND (o.shipped_on IS NULL OR o.shipped_on > s.snap_date)
GROUP BY s.snap_date, s.sku, s.on_hand
ORDER BY s.snap_date, s.sku;

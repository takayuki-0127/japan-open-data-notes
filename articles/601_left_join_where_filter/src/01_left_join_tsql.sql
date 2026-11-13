-- T-SQL：未検証（SQL Server では動かしていない）
-- W0 正しい：期間の条件を ON に置く
SELECT c.customer_id, ISNULL(SUM(o.amount), 0) AS amount, COUNT(o.order_id) AS orders
FROM dbo.customers AS c
LEFT JOIN dbo.orders AS o
  ON o.customer_id = c.customer_id
 AND o.order_date >= '2025-07-01' AND o.order_date < '2026-01-01'
GROUP BY c.customer_id;

-- 別の正しい書き方：先に期間で絞った注文を作ってからつなぐ
WITH o2 AS (
  SELECT customer_id, order_id, amount FROM dbo.orders
  WHERE order_date >= '2025-07-01' AND order_date < '2026-01-01')
SELECT c.customer_id, ISNULL(SUM(o2.amount), 0) AS amount, COUNT(o2.order_id) AS orders
FROM dbo.customers AS c LEFT JOIN o2 ON o2.customer_id = c.customer_id
GROUP BY c.customer_id;

-- W1 誤り：期間の条件を WHERE に置く（内部結合と同じ結果になる）
SELECT c.customer_id, ISNULL(SUM(o.amount), 0) AS amount
FROM dbo.customers AS c
LEFT JOIN dbo.orders AS o ON o.customer_id = c.customer_id
WHERE o.order_date >= '2025-07-01' AND o.order_date < '2026-01-01'
GROUP BY c.customer_id;

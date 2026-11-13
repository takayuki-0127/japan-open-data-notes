-- 顧客ごとの下期（2025-07-01〜12-31）の注文金額（DuckDB 版）。注文のない顧客も 0 で残したい
-- W0 正しい：期間の条件を ON に置く
SELECT c.customer_id, COALESCE(SUM(o.amount), 0) AS amount, COUNT(o.order_id) AS orders
FROM customers AS c
LEFT JOIN orders AS o
  ON o.customer_id = c.customer_id
 AND o.order_date >= DATE '2025-07-01' AND o.order_date < DATE '2026-01-01'
GROUP BY c.customer_id;
-- W1 よくある誤り：期間の条件を WHERE に置く（右の表が NULL の行が消え、内部結合と同じになる）
SELECT c.customer_id, COALESCE(SUM(o.amount), 0) AS amount, COUNT(o.order_id) AS orders
FROM customers AS c
LEFT JOIN orders AS o ON o.customer_id = c.customer_id
WHERE o.order_date >= DATE '2025-07-01' AND o.order_date < DATE '2026-01-01'
GROUP BY c.customer_id;
-- W2 半分直した誤り：WHERE に「OR o.order_id IS NULL」を足す（注文が1件もない顧客は残るが、期間の外にだけ注文がある顧客は消える）
SELECT c.customer_id, COALESCE(SUM(o.amount), 0) AS amount, COUNT(o.order_id) AS orders
FROM customers AS c
LEFT JOIN orders AS o ON o.customer_id = c.customer_id
WHERE (o.order_date >= DATE '2025-07-01' AND o.order_date < DATE '2026-01-01') OR o.order_id IS NULL
GROUP BY c.customer_id;

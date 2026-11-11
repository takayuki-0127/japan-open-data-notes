-- 03 合わないときの点検（T-SQL）。上から順に1つずつ流す
-- name: c1_counts  ①件数：注文の数と行の数を、結合の前後で数える
SELECT 'orders only' AS step, COUNT(*) AS n_rows, COUNT(DISTINCT o.order_id) AS n_orders
FROM dbo.orders AS o WHERE o.ordered_at BETWEEN '2026-03-01' AND '2026-03-31'
UNION ALL
SELECT '+ order_lines', COUNT(*), COUNT(DISTINCT o.order_id)
FROM dbo.orders AS o JOIN dbo.order_lines AS l ON l.order_id = o.order_id
WHERE o.ordered_at BETWEEN '2026-03-01' AND '2026-03-31'
UNION ALL
SELECT '+ customer_addresses', COUNT(*), COUNT(DISTINCT o.order_id)
FROM dbo.orders AS o JOIN dbo.order_lines AS l ON l.order_id = o.order_id
JOIN dbo.customer_addresses AS a ON a.customer_id = o.customer_id
WHERE o.ordered_at BETWEEN '2026-03-01' AND '2026-03-31'
UNION ALL
SELECT '+ stores', COUNT(*), COUNT(DISTINCT o.order_id)
FROM dbo.orders AS o JOIN dbo.order_lines AS l ON l.order_id = o.order_id
JOIN dbo.customer_addresses AS a ON a.customer_id = o.customer_id
JOIN dbo.stores AS s ON s.store_id = o.store_id
WHERE o.ordered_at BETWEEN '2026-03-01' AND '2026-03-31';
-- name: c2_dupkeys  ②結合キーの重複：1人に住所が何件あるか
SELECT n_addr, COUNT(*) AS n_customers
FROM (SELECT customer_id, COUNT(*) AS n_addr FROM dbo.customer_addresses GROUP BY customer_id) AS t
GROUP BY n_addr
ORDER BY n_addr;
-- name: c3_range  ③期間の端：抽出した注文の最初と最後の時刻
SELECT MIN(ordered_at) AS first_at, MAX(ordered_at) AS last_at
FROM dbo.orders WHERE ordered_at BETWEEN '2026-03-01' AND '2026-03-31';
-- name: c4_status  ④状態ごとの件数と金額
SELECT o.status, COUNT(DISTINCT o.order_id) AS n_orders, SUM(l.qty * l.unit_price) AS net
FROM dbo.orders AS o JOIN dbo.order_lines AS l ON l.order_id = o.order_id
WHERE o.ordered_at >= '2026-03-01' AND o.ordered_at < '2026-04-01'
GROUP BY o.status
ORDER BY o.status;
-- name: c5_nullkey  ⑤結合キーが NULL の行：店のない注文（ネット注文）
SELECT CASE WHEN store_id IS NULL THEN N'NULL（ネット）' ELSE N'店あり' END AS store, COUNT(*) AS n_orders
FROM dbo.orders WHERE ordered_at >= '2026-03-01' AND ordered_at < '2026-04-01' AND status = N'完了'
GROUP BY CASE WHEN store_id IS NULL THEN N'NULL（ネット）' ELSE N'店あり' END
ORDER BY 1;

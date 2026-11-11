-- 01 直す前の「3月の売上（税込）」レポート（T-SQL）。会計の数字と合わない
SELECT SUM(l.qty * l.unit_price * (1 + l.tax_rate)) AS sales_incl_tax
FROM dbo.orders AS o
JOIN dbo.order_lines        AS l ON l.order_id    = o.order_id
JOIN dbo.customer_addresses AS a ON a.customer_id = o.customer_id
JOIN dbo.stores             AS s ON s.store_id    = o.store_id
WHERE o.ordered_at BETWEEN '2026-03-01' AND '2026-03-31';

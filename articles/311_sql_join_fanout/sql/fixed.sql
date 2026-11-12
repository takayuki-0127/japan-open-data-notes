-- 直した書き方。T-SQL の書き方。DuckDB で実行して確かめた（SQL Server 本体では未検証）
-- name: S1_明細をつないで注文の送料を足す
SELECT SUM(o.shipping_fee) AS total
FROM dbo.orders AS o
WHERE EXISTS (SELECT 1 FROM dbo.order_items AS i WHERE i.order_id = o.order_id);

-- name: S2_支払をつないで注文の金額を足す
SELECT SUM(o.order_amount) AS total
FROM dbo.orders AS o
LEFT JOIN (SELECT order_id, SUM(paid_amount) AS paid
           FROM dbo.payments GROUP BY order_id) AS p ON p.order_id = o.order_id;

-- name: S3_明細と支払を両方つないで明細の金額を足す
SELECT SUM(i.items_amount) AS total
FROM dbo.orders AS o
JOIN (SELECT order_id, SUM(line_amount) AS items_amount
      FROM dbo.order_items GROUP BY order_id) AS i ON i.order_id = o.order_id
LEFT JOIN (SELECT order_id, SUM(paid_amount) AS paid
           FROM dbo.payments GROUP BY order_id) AS p ON p.order_id = o.order_id;

-- name: S4_店マスタを内部結合して注文の金額を足す
SELECT SUM(o.order_amount) AS total
FROM dbo.orders AS o
LEFT JOIN dbo.stores AS s ON s.store_code = o.store_code;

-- name: S5_履歴つきの店マスタを外部結合して注文の金額を足す
SELECT SUM(o.order_amount) AS total
FROM dbo.orders AS o
LEFT JOIN dbo.store_history AS h
       ON h.store_code = o.store_code AND h.is_current = 1;

-- name: S6_履歴つきの店マスタを内部結合して注文の金額を足す
SELECT SUM(o.order_amount) AS total
FROM dbo.orders AS o
LEFT JOIN dbo.store_history AS h
       ON h.store_code = o.store_code AND h.is_current = 1;

-- name: S7_増える分と消える分が打ち消し合う（履歴が少しだけある店マスタを内部結合）
SELECT SUM(o.order_amount) AS total
FROM dbo.orders AS o
LEFT JOIN dbo.store_history_small AS h
       ON h.store_code = o.store_code AND h.is_current = 1;

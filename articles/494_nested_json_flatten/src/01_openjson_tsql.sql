-- 494：入れ子の JSON を、注文・明細・クーポンの3つの表に分ける（T-SQL、未検証：SQL Server では動かしていない）
DECLARE @j NVARCHAR(MAX) = (SELECT BulkColumn FROM OPENROWSET(BULK 'C:\data\fictional_orders.json', SINGLE_CLOB) x);

-- 注文（1注文1行）
SELECT o.order_id, o.customer, o.shipping, o.order_total
FROM OPENJSON(@j) WITH (order_id INT, customer NVARCHAR(10), shipping INT, order_total INT) o;

-- 明細（1明細1行）
SELECT o.order_id, i.sku, i.qty, i.price, i.amount
FROM OPENJSON(@j) WITH (order_id INT, items NVARCHAR(MAX) AS JSON) o
CROSS APPLY OPENJSON(o.items) WITH (sku NVARCHAR(10), qty INT, price INT, amount INT) i;

-- クーポン（1枚1行）。クーポンのない注文は出てこない
SELECT o.order_id, c.code, c.discount
FROM OPENJSON(@j) WITH (order_id INT, coupons NVARCHAR(MAX) AS JSON) o
CROSS APPLY OPENJSON(o.coupons) WITH (code NVARCHAR(10), discount INT) c;
-- 明細とクーポンを同じ SELECT で2回 CROSS APPLY すると、明細×クーポンの組み合わせになり、合計がふくらむ

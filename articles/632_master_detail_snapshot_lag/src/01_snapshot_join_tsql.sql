-- T-SQL：未検証（SQL Server では動かしていない）
-- J1 内部結合
SELECT COUNT(*) AS n, SUM(amount) AS amt FROM dbo.orders_snap AS o JOIN dbo.customers_snap AS c ON c.customer_id = o.customer_id;
-- J2 外部結合（マスタにない顧客は「不明」）
SELECT COUNT(*) AS n, SUM(amount) AS amt, SUM(CASE WHEN c.region IS NULL THEN 1 ELSE 0 END) AS n_unknown
FROM dbo.orders_snap AS o LEFT JOIN dbo.customers_snap AS c ON c.customer_id = o.customer_id;

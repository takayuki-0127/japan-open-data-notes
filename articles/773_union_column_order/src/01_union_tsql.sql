-- T-SQL：未検証（SQL Server には UNION BY NAME はないので、列名を書く）
SELECT sale_date, store, item, qty, amount FROM dbo.store_a
UNION ALL
SELECT sale_date, store, item, qty, amount FROM dbo.store_b;
-- SELECT * でつなぐと、列の位置で合わさる（store_b は amount, qty の順）

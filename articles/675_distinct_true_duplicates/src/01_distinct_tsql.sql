-- T-SQL：未検証
SELECT 'D1' AS method, COUNT(*) AS n_rows, SUM(amount) AS amount
FROM (SELECT DISTINCT store, [date], [minute], item_name, qty, amount FROM dbo.sales_lines) AS d1
UNION ALL
SELECT 'D2', COUNT(*), SUM(amount)
FROM (SELECT DISTINCT store, [date], [time], item_name, qty, amount FROM dbo.sales_lines) AS d2
UNION ALL
SELECT 'T', COUNT(*), SUM(amount)
FROM (SELECT *, ROW_NUMBER() OVER (PARTITION BY txn_id ORDER BY txn_id) AS rn FROM dbo.sales_lines) AS t
WHERE rn = 1;

-- 重複の消し方3通りの件数と金額（DuckDB）
SELECT 'D1' AS method, COUNT(*) AS n_rows, SUM(amount) AS amount
FROM (SELECT DISTINCT store, date, minute, item_name, qty, amount FROM sales_lines)
UNION ALL
SELECT 'D2', COUNT(*), SUM(amount)
FROM (SELECT DISTINCT store, date, time, item_name, qty, amount FROM sales_lines)
UNION ALL
SELECT 'T', COUNT(*), SUM(amount)
FROM (SELECT * FROM (SELECT *, ROW_NUMBER() OVER (PARTITION BY txn_id ORDER BY txn_id) AS rn FROM sales_lines) WHERE rn = 1);

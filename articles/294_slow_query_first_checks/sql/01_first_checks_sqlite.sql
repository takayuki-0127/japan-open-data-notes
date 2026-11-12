-- この記事で実際に動かした SQLite 版（src/a294_cases.py と同じ）
EXPLAIN QUERY PLAN SELECT COUNT(*), SUM(amount) FROM orders WHERE customer_id = 12345;  -- SCAN orders
CREATE INDEX ix_cust ON orders(customer_id); ANALYZE;
EXPLAIN QUERY PLAN SELECT COUNT(*), SUM(amount) FROM orders WHERE customer_id = 12345;  -- SEARCH ... USING INDEX ix_cust
-- 列に関数：SCAN になる
EXPLAIN QUERY PLAN SELECT SUM(amount) FROM orders WHERE strftime('%Y-%m', order_date) = '2025-03';
-- 範囲の条件：SEARCH になる（ix_date がある場合）
EXPLAIN QUERY PLAN SELECT SUM(amount) FROM orders WHERE order_date >= '2025-03-01' AND order_date < '2025-04-01';

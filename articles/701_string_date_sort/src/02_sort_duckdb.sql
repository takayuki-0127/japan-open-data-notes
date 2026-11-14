-- 0を埋めない日付の文字列（例 2024/1/5）を、文字列のまま並べるか日付に直して並べるか（DuckDB 版）
-- orders(order_id, order_date_txt, amount)
SELECT order_id, order_date_txt,
       ROW_NUMBER() OVER (ORDER BY order_date_txt, order_id)                              AS pos_text,
       ROW_NUMBER() OVER (ORDER BY strptime(order_date_txt, '%Y/%-m/%-d'), order_id)       AS pos_date
FROM orders
ORDER BY order_id;
-- 最初と最後の日：文字列の MIN/MAX と、日付に直した MIN/MAX
SELECT MIN(order_date_txt) AS min_text, MAX(order_date_txt) AS max_text,
       strftime(MIN(strptime(order_date_txt, '%Y/%-m/%-d')), '%Y/%-m/%-d') AS min_date,
       strftime(MAX(strptime(order_date_txt, '%Y/%-m/%-d')), '%Y/%-m/%-d') AS max_date
FROM orders;

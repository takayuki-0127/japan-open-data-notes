-- T-SQL：未検証（SQL Server では動かしていない）
-- order_date_txt は varchar（例 '2024/1/5'）。CONVERT のスタイル 111 は yyyy/mm/dd
SELECT order_id, order_date_txt,
       ROW_NUMBER() OVER (ORDER BY order_date_txt, order_id)                          AS pos_text,
       ROW_NUMBER() OVER (ORDER BY TRY_CONVERT(date, order_date_txt, 111), order_id)   AS pos_date
FROM dbo.orders
ORDER BY order_id;

SELECT MIN(order_date_txt) AS min_text, MAX(order_date_txt) AS max_text,
       MIN(TRY_CONVERT(date, order_date_txt, 111)) AS min_date,
       MAX(TRY_CONVERT(date, order_date_txt, 111)) AS max_date
FROM dbo.orders;

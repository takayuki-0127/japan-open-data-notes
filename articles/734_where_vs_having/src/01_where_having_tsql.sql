-- T-SQL：未検証（SQL Server では動かしていない）
DECLARE @th int = 10000;
-- 1回 1万円以上の注文がある顧客
SELECT DISTINCT customer_id FROM orders WHERE amount >= @th;
-- 合計 1万円以上の顧客
SELECT customer_id, SUM(amount) AS total FROM orders GROUP BY customer_id HAVING SUM(amount) >= @th;
-- まちがいやすい例：WHERE で 1万円未満の注文を落としてから合計するので、合計の条件が別のものになる
SELECT customer_id, SUM(amount) AS total FROM orders WHERE amount >= @th GROUP BY customer_id HAVING SUM(amount) >= @th;

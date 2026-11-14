-- 顧客ごとの注文数を、COUNT(*) と COUNT(注文の列) で数える（DuckDB）
SELECT c.customer_id, c.signup_month,
       COUNT(*)          AS n_count_star,     -- 注文のない顧客も1と数える
       COUNT(o.order_id) AS n_count_col       -- 注文のない顧客は0
FROM customers AS c
LEFT JOIN orders AS o ON o.customer_id = c.customer_id
GROUP BY c.customer_id, c.signup_month
ORDER BY c.customer_id;

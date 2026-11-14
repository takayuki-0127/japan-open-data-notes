-- T-SQL：未検証
SELECT c.customer_id, c.signup_month,
       COUNT(*)          AS n_count_star,     -- 注文のない顧客も1と数える
       COUNT(o.order_id) AS n_count_col       -- 注文のない顧客は0
FROM dbo.customers AS c
LEFT JOIN dbo.orders AS o ON o.customer_id = c.customer_id
GROUP BY c.customer_id, c.signup_month
ORDER BY c.customer_id;

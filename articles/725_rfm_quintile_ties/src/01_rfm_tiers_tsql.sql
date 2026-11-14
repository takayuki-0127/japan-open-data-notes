-- T-SQL：未検証（SQL Server では動かしていない）
SELECT customer_id, freq,
       NTILE(5) OVER (ORDER BY freq DESC, customer_id)                   AS ntile_id,
       NTILE(5) OVER (ORDER BY freq DESC, last_date DESC, customer_id)   AS ntile_recent,
       CAST(FLOOR((RANK() OVER (ORDER BY freq DESC) - 1) * 5.0 / COUNT(*) OVER ()) AS int) + 1 AS rank_tier
FROM customers
ORDER BY customer_id;

-- 段の境目で同じ回数の人が分かれていないかを確かめる
WITH t AS (SELECT freq, NTILE(5) OVER (ORDER BY freq DESC, customer_id) AS tier FROM customers)
SELECT freq, COUNT(DISTINCT tier) AS tiers, COUNT(*) AS customers
FROM t GROUP BY freq HAVING COUNT(DISTINCT tier) > 1;

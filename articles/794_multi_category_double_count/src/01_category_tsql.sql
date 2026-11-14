-- T-SQL：未検証
WITH k AS (SELECT product_id, COUNT(*) AS n_cat FROM dbo.product_category GROUP BY product_id)
SELECT pc.category,
       SUM(s.amount)                                                   AS sales_join,
       SUM(CASE WHEN pc.is_primary = 1 THEN s.amount ELSE 0 END)       AS sales_primary,
       SUM(s.amount * 1.0 / k.n_cat)                                   AS sales_alloc
FROM dbo.sales AS s
JOIN dbo.product_category AS pc ON pc.product_id = s.product_id
JOIN k ON k.product_id = s.product_id
GROUP BY pc.category
ORDER BY pc.category;

-- カテゴリ別の売上を3通りで出す（DuckDB）
WITH k AS (SELECT product_id, COUNT(*) AS n_cat FROM product_category GROUP BY product_id)
SELECT pc.category,
       SUM(s.amount)                                                   AS sales_join,     -- そのまま結合して合計
       SUM(CASE WHEN pc.is_primary THEN s.amount ELSE 0 END)           AS sales_primary,  -- 主なカテゴリだけ
       SUM(s.amount * 1.0 / k.n_cat)                                   AS sales_alloc     -- カテゴリの数で按分
FROM sales AS s
JOIN product_category AS pc ON pc.product_id = s.product_id
JOIN k ON k.product_id = s.product_id
GROUP BY pc.category
ORDER BY pc.category;

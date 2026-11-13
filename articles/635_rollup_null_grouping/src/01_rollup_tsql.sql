-- T-SQL：未検証（SQL Server では動かしていない）
SELECT store, category,
       GROUPING(store) AS g_store, GROUPING(category) AS g_cat,
       CASE WHEN GROUPING(category) = 1 THEN N'（小計）'
            WHEN category IS NULL THEN N'（未分類）'
            ELSE category END AS category_label,
       SUM(amount) AS amount, COUNT(*) AS n
FROM dbo.sales
GROUP BY ROLLUP (store, category)
ORDER BY GROUPING(store), store, GROUPING(category), category;

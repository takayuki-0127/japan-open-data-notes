-- DuckDB：店×区分の ROLLUP。GROUPING() で小計の行と、区分がもともと空の行を見分ける
SELECT store, category,
       GROUPING(store) AS g_store, GROUPING(category) AS g_cat,
       SUM(amount) AS amount, COUNT(*) AS n
FROM sales
GROUP BY ROLLUP (store, category)
ORDER BY store NULLS LAST, g_cat, category NULLS LAST;

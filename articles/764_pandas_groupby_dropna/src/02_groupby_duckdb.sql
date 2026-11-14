-- SQL の GROUP BY は、欠けたキー（NULL）を1つのまとまりとして残す（DuckDB 版）
-- lines(ym, store, category, amount)
SELECT store, SUM(amount) AS amount FROM lines GROUP BY store ORDER BY store NULLS LAST;
-- 集計の前に、キーの欠けを数えておく
SELECT COUNT(*) FILTER (WHERE store IS NULL) AS n_null_store,
       COUNT(*) FILTER (WHERE category IS NULL) AS n_null_category
FROM lines;

-- T-SQL：未検証
SELECT store,
       COUNT(*) AS n_rows,
       SUM(TRY_CAST(amount AS bigint)) AS sum_numbers_only,
       SUM(COALESCE(TRY_CAST(REPLACE(amount, ',', '') AS bigint), 0)) AS sum_cleaned,
       SUM(CASE WHEN TRY_CAST(amount AS bigint) IS NULL THEN 1 ELSE 0 END) AS n_text
FROM dbo.sales
GROUP BY store
ORDER BY store;

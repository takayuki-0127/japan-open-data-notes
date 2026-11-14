-- 文字がまざった金額の列を数に直してから、店ごとに合計する（DuckDB）
SELECT store,
       COUNT(*)                                                             AS n_rows,
       SUM(TRY_CAST(amount AS BIGINT))                                      AS sum_numbers_only,   -- 数として読める行だけ
       SUM(COALESCE(TRY_CAST(REPLACE(amount, ',', '') AS BIGINT), 0))       AS sum_cleaned,        -- カンマを除いて数に直す（「-」は0）
       COUNT(*) FILTER (WHERE TRY_CAST(amount AS BIGINT) IS NULL)           AS n_text
FROM sales
GROUP BY store
ORDER BY store;

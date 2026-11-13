-- 例の1回の予測から、確かめ方ごとの平均絶対誤差（MAE）を数える（DuckDB）
SELECT method,
       COUNT(*)                  AS n,
       AVG(ABS(actual - pred))   AS mae
FROM preds
GROUP BY method
ORDER BY method;

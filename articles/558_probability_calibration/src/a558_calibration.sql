-- 予測確率を10%ごとに区切った較正表と、Brier スコア（DuckDB で実行）
WITH b AS (
    SELECT LEAST(CAST(FLOOR(pred * 10) AS INTEGER), 9) AS bin, pred, churned
    FROM predictions
)
SELECT bin,
       COUNT(*)                                   AS n_members,
       AVG(pred)                                  AS mean_pred,
       AVG(churned::DOUBLE)                       AS actual_rate,
       (SELECT AVG((pred - churned) * (pred - churned)) FROM predictions) AS brier
FROM b
GROUP BY bin
ORDER BY bin;

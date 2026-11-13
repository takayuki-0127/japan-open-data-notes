-- テスト用データの AUC を、スコアの順位から数える（DuckDB）
-- AUC =（正例の順位の合計 − 正例の数×(正例の数+1)/2）÷（正例の数×負例の数）
WITH r AS (
    SELECT y, AVG(rk) OVER (PARTITION BY score) AS rank_avg
    FROM (SELECT y, score, ROW_NUMBER() OVER (ORDER BY score) AS rk FROM pred)
)
SELECT (SUM(CASE WHEN y = 1 THEN rank_avg END)
        - SUM(y) * (SUM(y) + 1) / 2.0)
       / (SUM(y) * (COUNT(*) - SUM(y))) AS auc
FROM r;

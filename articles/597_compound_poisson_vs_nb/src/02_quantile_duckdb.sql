-- 年ごとの総損害のシミュレーション結果から、モデル別の平均・99.5%点・件数の分散÷平均を出す（DuckDB）
-- 表 simulated_years(model, year_id, claim_count, total_loss)
SELECT model,
       COUNT(*)                                   AS n_years,
       AVG(total_loss)                            AS mean_total,
       QUANTILE_CONT(total_loss, 0.99)            AS q99,
       QUANTILE_CONT(total_loss, 0.995)           AS q995,
       VAR_SAMP(claim_count) / AVG(claim_count)   AS count_var_over_mean
FROM simulated_years
GROUP BY model
ORDER BY model;

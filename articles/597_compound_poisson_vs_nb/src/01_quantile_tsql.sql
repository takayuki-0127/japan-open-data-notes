-- 年ごとの総損害のシミュレーション結果から、モデル別の平均・99.5%点・件数の分散÷平均を出す
-- （T-SQL、未検証：SQL Server では動かしていない）。PERCENTILE_CONT は分析関数なので DISTINCT でまとめる
SELECT DISTINCT model,
       COUNT(*)            OVER (PARTITION BY model)                                   AS n_years,
       AVG(total_loss)     OVER (PARTITION BY model)                                   AS mean_total,
       PERCENTILE_CONT(0.99)  WITHIN GROUP (ORDER BY total_loss) OVER (PARTITION BY model) AS q99,
       PERCENTILE_CONT(0.995) WITHIN GROUP (ORDER BY total_loss) OVER (PARTITION BY model) AS q995,
       VAR(CAST(claim_count AS float)) OVER (PARTITION BY model)
         / AVG(CAST(claim_count AS float)) OVER (PARTITION BY model)                    AS count_var_over_mean
FROM dbo.simulated_years
ORDER BY model;

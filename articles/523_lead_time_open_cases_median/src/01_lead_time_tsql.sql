-- T-SQL 版（SQL Server では動かしていない：未検証）
-- dbo.cases(received date, done_obs date NULL)：締めの日までに終わっていなければ done_obs は NULL
-- 完了分だけの中央値（未完了は落ちる）と、未完了の件数・締めの日までの経過日数
WITH c AS (
    SELECT received, done_obs,
           DATEDIFF(DAY, received, COALESCE(done_obs, '2025-12-31')) AS days_observed,
           CASE WHEN done_obs IS NULL THEN 0 ELSE 1 END              AS is_done
    FROM dbo.cases
    WHERE received >= '2025-01-01' AND received < '2026-01-01'
)
SELECT DISTINCT
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY CASE WHEN is_done = 1 THEN days_observed END) OVER () AS median_completed_only,
    SUM(1 - is_done) OVER () AS open_cases,
    COUNT(*) OVER ()         AS all_cases
FROM c;
-- カプラン・マイヤーは days_observed と is_done を出して Python 側で計算した（a523_lead_time.py の km_median）

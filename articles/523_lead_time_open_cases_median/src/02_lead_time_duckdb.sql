-- 2025年受注の案件の、2025-12-31 締めでの「完了分だけの中央値」と未完了の件数（DuckDB で実行）
-- cases(received, done_obs)：done_obs は締めの日までに終わっていれば完了日、終わっていなければ NULL
SELECT
    MEDIAN(date_diff('day', received, done_obs)) FILTER (WHERE done_obs IS NOT NULL) AS median_completed_only,
    COUNT(*) FILTER (WHERE done_obs IS NULL)                                          AS open_cases,
    COUNT(*)                                                                          AS all_cases
FROM cases
WHERE received >= DATE '2025-01-01' AND received < DATE '2026-01-01';

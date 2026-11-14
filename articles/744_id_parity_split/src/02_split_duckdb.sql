-- 会員を2群に分ける3つの方法と、群ごとの平均（DuckDB）。施策はしていない（A/A の比較）
SELECT 'parity' AS method, member_id % 2 AS grp, COUNT(*) AS n, AVG(spend) AS mean_spend, VAR_SAMP(spend) AS var_spend
FROM members GROUP BY member_id % 2
UNION ALL
SELECT 'hash', hash(member_id::VARCHAR || '-exp744') % 2, COUNT(*), AVG(spend), VAR_SAMP(spend)
FROM members GROUP BY hash(member_id::VARCHAR || '-exp744') % 2
ORDER BY method, grp;

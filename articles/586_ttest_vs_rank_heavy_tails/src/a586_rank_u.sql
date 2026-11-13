-- 2群の順位の検定（Mann–Whitney）の U を、順位から数える（DuckDB）
-- 同じ値がないデータを想定（同じ値があるときは順位の平均を使う）
WITH r AS (
    SELECT grp, value, AVG(rk) OVER (PARTITION BY value) AS rank_avg
    FROM (SELECT grp, value, ROW_NUMBER() OVER (ORDER BY value) AS rk FROM obs)
)
SELECT SUM(rank_avg) - COUNT(*) * (COUNT(*) + 1) / 2.0 AS u_group_a
FROM r
WHERE grp = 'A';

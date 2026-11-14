-- 区分ごとのユニークな人数を、正確な数と近似で数える（DuckDB）
SELECT segment,
       COUNT(*)                     AS n_rows,
       COUNT(DISTINCT user_id)      AS exact_users,
       approx_count_distinct(user_id) AS approx_users
FROM access_log
GROUP BY segment
ORDER BY segment;
-- 全体のユニークな人数（区分の近似を足すのではなく、全体で数え直す）
SELECT COUNT(DISTINCT user_id) AS exact_users, approx_count_distinct(user_id) AS approx_users FROM access_log;

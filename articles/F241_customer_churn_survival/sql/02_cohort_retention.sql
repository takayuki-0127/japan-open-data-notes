-- 設立年（コホート）×経過年の定着率表（SQL Server でも動く書き方）
-- houjin(cohort, kind_j, months, event)：months は設立から閉鎖または観察の終わりまでの月数
WITH yrs AS (
    SELECT 1 AS y UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4 UNION ALL SELECT 5
    UNION ALL SELECT 6 UNION ALL SELECT 7 UNION ALL SELECT 8 UNION ALL SELECT 9 UNION ALL SELECT 10
), base AS (
    SELECT kind_j, cohort, COUNT(*) AS n FROM houjin GROUP BY kind_j, cohort
), closed AS (
    SELECT h.kind_j, h.cohort, y.y,
           SUM(CASE WHEN h.event = 1 AND h.months < 12 * y.y THEN 1 ELSE 0 END) AS closed_n
    FROM houjin AS h CROSS JOIN yrs AS y
    WHERE (2026 - h.cohort - 1) * 12 + 9 >= 12 * y.y      -- 全員が y 年観察できるコホートだけ（観察の終わり 2026-09-30）
    GROUP BY h.kind_j, h.cohort, y.y
)
SELECT c.kind_j, c.cohort, c.y AS year, b.n, 1.0 - CAST(c.closed_n AS FLOAT) / b.n AS retention
FROM closed AS c JOIN base AS b ON b.kind_j = c.kind_j AND b.cohort = c.cohort
ORDER BY c.kind_j, c.cohort, c.y;

-- T-SQL 版（SQL Server では動かしていない：未検証）
-- 月ごとのユニーク利用者を Cookie・ログインID・つなぎ合わせたIDで数える
WITH stitch AS (            -- 一度でもログインした Cookie を人に結びつける
    SELECT cookie, MIN(person) AS person
    FROM dbo.logs
    WHERE login = 1
    GROUP BY cookie
)
SELECT FORMAT(l.[date], 'yyyy-MM')                          AS ym,
       COUNT(DISTINCT l.cookie)                              AS cookie_users,
       COUNT(DISTINCT CASE WHEN l.login = 1 THEN l.person END) AS login_users,
       COUNT(DISTINCT COALESCE('p' + CAST(s.person AS varchar(20)),
                               'c' + CAST(l.cookie AS varchar(20)))) AS stitched_users
FROM dbo.logs AS l
LEFT JOIN stitch AS s ON s.cookie = l.cookie
GROUP BY FORMAT(l.[date], 'yyyy-MM')
ORDER BY ym;

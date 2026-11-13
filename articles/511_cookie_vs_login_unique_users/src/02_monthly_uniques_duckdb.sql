-- 月ごとのユニーク利用者を、本当の人ID と Cookie で数える（DuckDB で実行）
SELECT strftime(date, '%Y-%m')      AS ym,
       COUNT(DISTINCT person)       AS true_users,
       COUNT(DISTINCT cookie)       AS cookie_users,
       COUNT(DISTINCT CASE WHEN login THEN person END) AS login_users,
       COUNT(*)                     AS visits
FROM logs
GROUP BY ym
ORDER BY ym;

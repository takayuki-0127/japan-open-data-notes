-- 契約の「在籍」を数える書き方。T-SQL の書き方。DuckDB で実行して確かめた（SQL Server 本体では未検証）
-- policies(policy_id, start_date, end_date)：end_date は保険期間が終わる日（解約した契約は解約日）。その日は在籍に含めない
-- months(month_start, next_month_start)：月の初日と翌月の初日
-- {FROM}＝年の初日、{TO}＝翌年の初日
-- name: A_日数で数える（経過契約年）
SELECT SUM(DATEDIFF(day,
           CASE WHEN p.start_date > '{FROM}' THEN p.start_date ELSE '{FROM}' END,
           CASE WHEN p.end_date   < '{TO}'   THEN p.end_date   ELSE '{TO}'   END)) / 365.0 AS v
FROM dbo.policies AS p
WHERE p.start_date < '{TO}' AND p.end_date > '{FROM}';

-- name: B_年初の在籍件数
SELECT COUNT(*) AS v FROM dbo.policies AS p
WHERE p.start_date <= '{FROM}' AND p.end_date > '{FROM}';

-- name: C_年末の在籍件数
SELECT COUNT(*) AS v FROM dbo.policies AS p
WHERE p.start_date < '{TO}' AND p.end_date >= '{TO}';

-- name: D_年初と年末の平均
SELECT (SUM(CASE WHEN p.start_date <= '{FROM}' AND p.end_date > '{FROM}' THEN 1 ELSE 0 END)
      + SUM(CASE WHEN p.start_date <  '{TO}'   AND p.end_date >= '{TO}'  THEN 1 ELSE 0 END)) / 2.0 AS v
FROM dbo.policies AS p;

-- name: E_月初の在籍件数の12か月平均
SELECT AVG(CAST(x.n AS FLOAT)) AS v
FROM (SELECT m.month_start, COUNT(*) AS n
      FROM dbo.months AS m
      JOIN dbo.policies AS p ON p.start_date <= m.month_start AND p.end_date > m.month_start
      WHERE m.month_start >= '{FROM}' AND m.month_start < '{TO}'
      GROUP BY m.month_start) AS x;

-- name: F_月初と月末の平均の12か月平均
SELECT AVG(x.n) AS v
FROM (SELECT m.month_start,
             (SUM(CASE WHEN p.start_date <= m.month_start AND p.end_date > m.month_start THEN 1 ELSE 0 END)
            + SUM(CASE WHEN p.start_date <  m.next_month_start AND p.end_date >= m.next_month_start THEN 1 ELSE 0 END)) / 2.0 AS n
      FROM dbo.months AS m
      JOIN dbo.policies AS p ON p.start_date < m.next_month_start AND p.end_date > m.month_start
      WHERE m.month_start >= '{FROM}' AND m.month_start < '{TO}'
      GROUP BY m.month_start) AS x;

-- name: G_その年に始まった契約の件数
SELECT COUNT(*) AS v FROM dbo.policies AS p
WHERE p.start_date >= '{FROM}' AND p.start_date < '{TO}';

-- name: H_その年に1日でも在籍した契約の件数
SELECT COUNT(*) AS v FROM dbo.policies AS p
WHERE p.start_date < '{TO}' AND p.end_date > '{FROM}';

-- 1年分の保険料を月ごとに分ける3つの書き方。T-SQL の書き方。DuckDB で実行して確かめた（SQL Server 本体では未検証）
-- policies(policy_id, start_date, end_date, premium)：end_date は始期の1年後（その日は保険期間に含めない）
-- months(month_start, next_month_start)
-- name: 日割り
SELECT m.month_start,
       SUM(p.premium * DATEDIFF(day,
             CASE WHEN p.start_date > m.month_start      THEN p.start_date ELSE m.month_start      END,
             CASE WHEN p.end_date   < m.next_month_start THEN p.end_date   ELSE m.next_month_start END)
           / CAST(DATEDIFF(day, p.start_date, p.end_date) AS FLOAT)) AS earned
FROM dbo.months AS m
JOIN dbo.policies AS p ON p.start_date < m.next_month_start AND p.end_date > m.month_start
GROUP BY m.month_start;

-- name: 12分の1（始期の月から12か月）
SELECT m.month_start, SUM(p.premium / 12.0) AS earned
FROM dbo.months AS m
JOIN dbo.policies AS p ON DATEDIFF(month, p.start_date, m.month_start) BETWEEN 0 AND 11
GROUP BY m.month_start;

-- name: 24分の1（始期の月と13か月目は半分）
SELECT m.month_start,
       SUM(p.premium * CASE WHEN DATEDIFF(month, p.start_date, m.month_start) IN (0, 12) THEN 1 ELSE 2 END / 24.0) AS earned
FROM dbo.months AS m
JOIN dbo.policies AS p ON DATEDIFF(month, p.start_date, m.month_start) BETWEEN 0 AND 12
GROUP BY m.month_start;

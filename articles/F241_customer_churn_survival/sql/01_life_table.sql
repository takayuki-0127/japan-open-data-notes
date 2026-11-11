-- 月ごとの生命表（SQL Server でも動く書き方：CTE・CASE・SUM のみ）
-- telco(customerID, duration, event)：duration は在籍月数、event は 1=解約
WITH months AS (
    SELECT DISTINCT duration AS month FROM telco WHERE duration BETWEEN 1 AND 72
), lt AS (
    SELECT m.month,
           SUM(CASE WHEN t.duration >= m.month THEN 1 ELSE 0 END) AS at_risk,
           SUM(CASE WHEN t.duration = m.month AND t.event = 1 THEN 1 ELSE 0 END) AS events
    FROM months AS m CROSS JOIN telco AS t
    GROUP BY m.month
)
SELECT month, at_risk, events, CAST(events AS FLOAT) / at_risk AS hazard
FROM lt
ORDER BY month;

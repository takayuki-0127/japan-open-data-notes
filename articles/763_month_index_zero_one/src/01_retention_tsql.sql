-- T-SQL：未検証（SQL Server では動かしていない）
-- 在籍した月の表 dbo.sub_months(customer_id, signup_month, active_month) がある前提
SELECT signup_month,
       DATEDIFF(month, signup_month, active_month)     AS month0,   -- 0始まり
       DATEDIFF(month, signup_month, active_month) + 1 AS month1,   -- 1始まり
       COUNT(*) AS active
FROM dbo.sub_months
GROUP BY signup_month, DATEDIFF(month, signup_month, active_month)
ORDER BY signup_month, month0;
-- 表の見出しには、どちらの数え方かを必ず書く（例：「加入月=0」「加入月=1か月目」）

-- 継続率の表を「0から数える」と「1から数える」で作る（DuckDB 版）
-- subs(customer_id, signup_month DATE（月初）, last_month DATE（最後に在籍した月の月初。継続中は NULL）)
-- 観察の最終月は 2025-12
WITH months AS (
  SELECT s.customer_id, s.signup_month, CAST(m.range AS DATE) AS active_month
  FROM subs s,
       range(s.signup_month, COALESCE(s.last_month, DATE '2025-12-01') + INTERVAL 1 MONTH, INTERVAL 1 MONTH) m),
idx AS (
  SELECT signup_month, customer_id,
         date_diff('month', signup_month, active_month)     AS month0,   -- 0始まり：加入した月が 0
         date_diff('month', signup_month, active_month) + 1 AS month1    -- 1始まり：加入した月が 1
  FROM months),
coh AS (SELECT signup_month, COUNT(*) AS n FROM subs GROUP BY signup_month)
SELECT i.signup_month, i.month0, i.month1, COUNT(*) AS active, c.n,
       ROUND(COUNT(*) * 100.0 / c.n, 2) AS retention_pct
FROM idx i JOIN coh c USING (signup_month)
GROUP BY i.signup_month, i.month0, i.month1, c.n
ORDER BY i.signup_month, i.month0;

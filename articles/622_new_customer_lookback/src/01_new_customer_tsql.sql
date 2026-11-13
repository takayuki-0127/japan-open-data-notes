-- T-SQL：未検証（SQL Server では動かしていない）
-- 新規の顧客の判定。dbo.buy_months(customer_id, ym)：購入のあった月（2018年1月を1とする通し番号）
-- 前回の購入から24か月より長くあいていれば（または前回がなければ）新規とみなす
WITH x AS (
  SELECT customer_id, ym,
         LAG(ym) OVER (PARTITION BY customer_id ORDER BY ym) AS prev_ym
  FROM dbo.buy_months
)
SELECT ym,
       COUNT(*) AS buyers,
       SUM(CASE WHEN prev_ym IS NULL OR ym - prev_ym > 24 THEN 1 ELSE 0 END) AS new_24m
FROM x
WHERE ym >= 85
GROUP BY ym
ORDER BY ym;

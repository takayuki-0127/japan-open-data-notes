-- 新規の顧客の判定（DuckDB 版）。buy_months(customer_id, ym)：購入のあった月（ym は 2018年1月を1とする月の通し番号）
-- 前回の購入から :k か月より長くあいていれば（または前回がなければ）新規とみなす
WITH x AS (
  SELECT customer_id, ym,
         LAG(ym) OVER (PARTITION BY customer_id ORDER BY ym) AS prev_ym
  FROM buy_months
)
SELECT ym,
       COUNT(*) AS buyers,
       SUM(CASE WHEN prev_ym IS NULL OR ym - prev_ym > 24 THEN 1 ELSE 0 END) AS new_24m
FROM x
WHERE ym >= 85          -- 2025年1月以降
GROUP BY ym
ORDER BY ym;

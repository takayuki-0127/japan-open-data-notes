-- 同じ金額の請求と入金に、それぞれ日付の順で番号を振り、金額と番号でつなぐ（DuckDB で実行）
WITH i AS (
  SELECT inv, amount, due, ROW_NUMBER() OVER (PARTITION BY amount ORDER BY due, inv) AS rn FROM inv
), p AS (
  SELECT pay, amount, date, true_inv, ROW_NUMBER() OVER (PARTITION BY amount ORDER BY date, pay) AS rn FROM pay
)
SELECT p.pay, p.true_inv, i.inv
FROM p LEFT JOIN i ON i.amount = p.amount AND i.rn = p.rn
ORDER BY p.pay

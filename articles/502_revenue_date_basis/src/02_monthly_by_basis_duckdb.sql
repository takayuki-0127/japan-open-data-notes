-- 同じ注文を、受注日・出荷日・検収日の3つで月に集計する（DuckDB で実行）
SELECT kind, basis, strftime(d, '%Y-%m') AS ym, SUM(amount) AS amount
FROM (
  UNPIVOT orders ON order_date, ship_date, accept_date INTO NAME basis VALUE d
)
WHERE d BETWEEN DATE '2023-01-01' AND DATE '2025-12-31'
GROUP BY ALL
ORDER BY kind, basis, ym

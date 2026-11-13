-- 初回購入月を「全部の注文」と「確定だけ」で決め、月ごとの新規の数を並べる（DuckDB で実行）
WITH f_all AS (
  SELECT member, strftime(MIN(ordered_at), '%Y-%m') AS ym FROM orders GROUP BY member
), f_conf AS (
  SELECT member, strftime(MIN(ordered_at), '%Y-%m') AS ym FROM orders
  WHERE status = '確定' AND NOT is_test GROUP BY member
)
SELECT ym,
       COUNT(*) FILTER (WHERE src = 'all')  AS new_all,
       COUNT(*) FILTER (WHERE src = 'conf') AS new_confirmed
FROM (SELECT ym, 'all' AS src FROM f_all UNION ALL SELECT ym, 'conf' FROM f_conf)
GROUP BY ym ORDER BY ym

-- CASE WHEN の条件の並べ方（DuckDB 版）。cust(customer_id, spend, orders, days_since_last, days_since_first)
-- 並べ方A：VIP → 常連 → 新規 → 休眠
SELECT seg, COUNT(*) AS n FROM (
  SELECT CASE WHEN spend >= 100000 THEN 'VIP'
              WHEN orders >= 6 THEN '常連'
              WHEN days_since_first <= 90 THEN '新規'
              WHEN days_since_last > 180 THEN '休眠'
              ELSE 'その他' END AS seg
  FROM cust) GROUP BY seg ORDER BY seg;
-- 並べ方B：休眠 → 新規 → 常連 → VIP
SELECT seg, COUNT(*) AS n FROM (
  SELECT CASE WHEN days_since_last > 180 THEN '休眠'
              WHEN days_since_first <= 90 THEN '新規'
              WHEN orders >= 6 THEN '常連'
              WHEN spend >= 100000 THEN 'VIP'
              ELSE 'その他' END AS seg
  FROM cust) GROUP BY seg ORDER BY seg;
-- 重なりの確認：いくつの条件に当てはまるか
SELECT (spend >= 100000)::INT + (orders >= 6)::INT + (days_since_first <= 90)::INT + (days_since_last > 180)::INT AS k, COUNT(*) AS n
FROM cust GROUP BY k ORDER BY k;

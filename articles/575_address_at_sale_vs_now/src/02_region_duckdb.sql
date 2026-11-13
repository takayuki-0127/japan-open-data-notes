-- 売った時点の住所で、地域別・年別の売上を出す（DuckDB）。住所の履歴は有効期間つき（valid_to は次の住所の開始日）
SELECT a.region, YEAR(o.ordered_on) AS yr, SUM(o.amount) AS sales
FROM orders o
JOIN address_history a
  ON o.customer_id = a.customer_id
 AND a.valid_from <= o.ordered_on AND o.ordered_on < a.valid_to
GROUP BY 1, 2;
-- @now 今の住所（最後の履歴）で数える
SELECT a.region, YEAR(o.ordered_on) AS yr, SUM(o.amount) AS sales
FROM orders o
JOIN address_history a
  ON o.customer_id = a.customer_id AND a.valid_to = DATE '9999-12-31'
GROUP BY 1, 2;
-- @first 登録時の住所（最初の履歴）で数える
SELECT a.region, YEAR(o.ordered_on) AS yr, SUM(o.amount) AS sales
FROM orders o
JOIN (SELECT customer_id, region,
             ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY valid_from) AS rn
      FROM address_history) a
  ON o.customer_id = a.customer_id AND a.rn = 1
GROUP BY 1, 2;

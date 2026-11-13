-- クーポン別の売上：全額を付ける／値引き額で按分（DuckDB）
WITH m AS (
  SELECT oc.coupon, oc.order_id, oc.discount, o.amount,
         oc.discount * 1.0 / SUM(oc.discount) OVER (PARTITION BY oc.order_id) AS share
  FROM order_coupons oc JOIN orders o USING (order_id)
)
SELECT coupon,
       SUM(amount)          AS full_amount,
       SUM(amount * share)  AS prop_amount
FROM m GROUP BY coupon ORDER BY coupon;

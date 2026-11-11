-- 02 会計の数字（比べる相手）：3月に受けて取消されていない注文。税は注文ごと・税率ごとに円未満切り捨て（T-SQL）
SELECT SUM(net + tax) AS sales_incl_tax
FROM (
    SELECT o.order_id, l.tax_rate,
           SUM(l.qty * l.unit_price)                    AS net,
           FLOOR(SUM(l.qty * l.unit_price) * l.tax_rate) AS tax
    FROM dbo.orders AS o
    JOIN dbo.order_lines AS l ON l.order_id = o.order_id
    WHERE o.ordered_at >= '2026-03-01' AND o.ordered_at < '2026-04-01'
      AND o.status = N'完了'
    GROUP BY o.order_id, l.tax_rate
) AS t;

-- 04 直したレポート（T-SQL）：住所は今の1件だけ、店は LEFT JOIN、期間は「以上・未満」、取消を除く、税は注文ごとに切り捨て
SELECT SUM(net + tax) AS sales_incl_tax
FROM (
    SELECT o.order_id, l.tax_rate,
           SUM(l.qty * l.unit_price)                    AS net,
           FLOOR(SUM(l.qty * l.unit_price) * l.tax_rate) AS tax
    FROM dbo.orders AS o
    JOIN dbo.order_lines             AS l ON l.order_id    = o.order_id
    JOIN dbo.customer_addresses      AS a ON a.customer_id = o.customer_id AND a.is_primary = 1
    LEFT JOIN dbo.stores             AS s ON s.store_id    = o.store_id
    WHERE o.ordered_at >= '2026-03-01' AND o.ordered_at < '2026-04-01'
      AND o.status = N'完了'
    GROUP BY o.order_id, l.tax_rate
) AS t;

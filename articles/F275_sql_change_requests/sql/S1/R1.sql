-- R1 全社の月次売上
SELECT c.cal_ym AS ym, SUM(x.amt) AS sales
FROM (
    SELECT l.date_key AS d, l.store_id, l.item_id, l.amount_incl AS amt
    FROM sales_line l
    WHERE l.status <> 'cancel'
    UNION ALL
    SELECT r.return_date_key AS d, l.store_id, l.item_id, -r.amount_incl AS amt
    FROM returns_line r
    JOIN sales_line l ON l.receipt_id = r.receipt_id AND l.line_no = r.line_no
    WHERE l.status <> 'cancel'
) x
JOIN calendar c ON c.date_key = x.d
GROUP BY c.cal_ym
ORDER BY c.cal_ym;

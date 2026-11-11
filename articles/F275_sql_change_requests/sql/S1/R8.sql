-- R8 直近月の日別売上
SELECT x.d AS date_key, SUM(x.amt) AS sales
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
WHERE c.cal_ym = (
    SELECT MAX(c2.cal_ym)
    FROM (
        SELECT l.date_key AS d, l.store_id, l.item_id, l.amount_incl AS amt
        FROM sales_line l
        WHERE l.status <> 'cancel'
        UNION ALL
        SELECT r.return_date_key AS d, l.store_id, l.item_id, -r.amount_incl AS amt
        FROM returns_line r
        JOIN sales_line l ON l.receipt_id = r.receipt_id AND l.line_no = r.line_no
        WHERE l.status <> 'cancel'
    ) x2
    JOIN calendar c2 ON c2.date_key = x2.d
)
GROUP BY x.d
ORDER BY x.d;

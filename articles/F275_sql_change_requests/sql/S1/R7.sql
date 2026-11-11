-- R7 KPI のまとめ
SELECT s.ym, s.sales, k.customers, s.sales * 1.0 / k.customers AS ticket, q.yoy AS comp_yoy
FROM (
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
) s
JOIN (
    SELECT c.cal_ym AS ym, COUNT(DISTINCT rc.receipt_id) AS customers
    FROM receipt rc
    JOIN calendar c ON c.date_key = rc.date_key
    WHERE EXISTS (SELECT 1 FROM sales_line l
                  WHERE l.receipt_id = rc.receipt_id AND l.status <> 'cancel')
    GROUP BY c.cal_ym
) k ON k.ym = s.ym
LEFT JOIN (
  SELECT a.ym, SUM(a.sales) * 1.0 / SUM(b.sales) - 1 AS yoy
  FROM (
      SELECT c.cal_ym AS ym, c.cal_mi AS mi, x.store_id, SUM(x.amt) AS sales
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
      GROUP BY c.cal_ym, c.cal_mi, x.store_id
  ) a
  JOIN (
      SELECT c.cal_ym AS ym, c.cal_mi AS mi, x.store_id, SUM(x.amt) AS sales
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
      GROUP BY c.cal_ym, c.cal_mi, x.store_id
  ) b ON b.store_id = a.store_id AND b.mi = a.mi - 12
  JOIN store cs ON cs.store_id = a.store_id
  JOIN calendar oc ON oc.date_key = cs.open_date_key
  WHERE oc.cal_mi <= a.mi - 13
  GROUP BY a.ym
) q ON q.ym = s.ym
ORDER BY s.ym;

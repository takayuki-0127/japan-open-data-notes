-- R1 全社の月次売上
WITH line_ok AS (
  SELECT l.receipt_id, l.line_no, l.date_key, l.store_id, l.item_id, l.amount_incl,
         1.0 AS amt_factor
  FROM sales_line l
  WHERE l.status <> 'cancel'
),
net AS (
  SELECT o.date_key AS d, o.store_id, o.item_id, o.amount_incl * o.amt_factor AS amt
  FROM line_ok o
  UNION ALL
  SELECT r.return_date_key AS d, o.store_id, o.item_id, -r.amount_incl * o.amt_factor AS amt
  FROM returns_line r
  JOIN line_ok o ON o.receipt_id = r.receipt_id AND o.line_no = r.line_no
),
mon AS (
  SELECT c.date_key, c.cal_ym AS ym, c.cal_mi AS mi
  FROM calendar c
)
SELECT m.ym, SUM(n.amt) AS sales
FROM net n
JOIN mon m ON m.date_key = n.d
GROUP BY m.ym
ORDER BY m.ym;

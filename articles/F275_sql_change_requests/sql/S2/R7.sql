-- R7 KPI のまとめ
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
),
comp_store AS (
  SELECT s.store_id, m.mi
  FROM store s
  JOIN mon om ON om.date_key = s.open_date_key
  CROSS JOIN (SELECT DISTINCT mi FROM mon) m
  WHERE om.mi <= m.mi - 13
),
cust AS (
  SELECT r.date_key, r.store_id,
         r.receipt_id AS cust_key
  FROM receipt r
  WHERE EXISTS (SELECT 1 FROM line_ok o WHERE o.receipt_id = r.receipt_id)
)
SELECT s.ym, s.sales, c.customers, s.sales * 1.0 / c.customers AS ticket, k.yoy AS comp_yoy
FROM (SELECT m.ym, SUM(n.amt) AS sales FROM net n JOIN mon m ON m.date_key = n.d GROUP BY m.ym) s
JOIN (SELECT m.ym, COUNT(DISTINCT u.cust_key) AS customers FROM cust u JOIN mon m ON m.date_key = u.date_key GROUP BY m.ym) c
  ON c.ym = s.ym
LEFT JOIN (
  SELECT a.ym, SUM(a.sales) * 1.0 / SUM(b.sales) - 1 AS yoy
  FROM (
    SELECT m.ym, m.mi, n.store_id, SUM(n.amt) AS sales
    FROM net n JOIN mon m ON m.date_key = n.d
    GROUP BY m.ym, m.mi, n.store_id
  ) a
  JOIN (
    SELECT m.ym, m.mi, n.store_id, SUM(n.amt) AS sales
    FROM net n JOIN mon m ON m.date_key = n.d
    GROUP BY m.ym, m.mi, n.store_id
  ) b ON b.store_id = a.store_id AND b.mi = a.mi - 12
  JOIN comp_store cs ON cs.store_id = a.store_id AND cs.mi = a.mi
  GROUP BY a.ym
) k ON k.ym = s.ym
ORDER BY s.ym;

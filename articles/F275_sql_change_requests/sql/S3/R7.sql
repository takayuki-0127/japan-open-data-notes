-- R7 KPI のまとめ
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

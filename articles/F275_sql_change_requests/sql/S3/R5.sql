-- R5 客数と客単価
SELECT s.ym, s.sales, c.customers, s.sales * 1.0 / c.customers AS ticket
FROM (SELECT m.ym, SUM(n.amt) AS sales FROM net n JOIN mon m ON m.date_key = n.d GROUP BY m.ym) s
JOIN (SELECT m.ym, COUNT(DISTINCT u.cust_key) AS customers FROM cust u JOIN mon m ON m.date_key = u.date_key GROUP BY m.ym) c
  ON c.ym = s.ym
ORDER BY s.ym;

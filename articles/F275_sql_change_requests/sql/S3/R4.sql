-- R4 既存店の前年比
SELECT a.ym, SUM(a.sales) AS comp_sales, SUM(b.sales) AS comp_sales_ly,
       SUM(a.sales) * 1.0 / SUM(b.sales) - 1 AS yoy
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
ORDER BY a.ym;

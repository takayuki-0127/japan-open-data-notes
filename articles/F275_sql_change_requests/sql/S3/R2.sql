-- R2 店舗別の月次売上
SELECT m.ym, n.store_id, SUM(n.amt) AS sales
FROM net n
JOIN mon m ON m.date_key = n.d
GROUP BY m.ym, n.store_id
ORDER BY m.ym, n.store_id;

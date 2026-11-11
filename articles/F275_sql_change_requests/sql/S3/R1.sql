-- R1 全社の月次売上
SELECT m.ym, SUM(n.amt) AS sales
FROM net n
JOIN mon m ON m.date_key = n.d
GROUP BY m.ym
ORDER BY m.ym;

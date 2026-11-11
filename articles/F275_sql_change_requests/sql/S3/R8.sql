-- R8 直近月の日別売上
SELECT n.d AS date_key, SUM(n.amt) AS sales
FROM net n
JOIN mon m ON m.date_key = n.d
WHERE m.ym = (SELECT MAX(m2.ym) FROM net n2 JOIN mon m2 ON m2.date_key = n2.d)
GROUP BY n.d
ORDER BY n.d;

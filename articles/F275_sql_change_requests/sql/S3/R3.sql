-- R3 部門グループ別の月次売上
SELECT m.ym, g.grp, SUM(n.amt) AS sales
FROM net n
JOIN mon m ON m.date_key = n.d
JOIN item i ON i.item_id = n.item_id
JOIN dept_grp g ON g.dept_id = i.dept_id
GROUP BY m.ym, g.grp
ORDER BY m.ym, g.grp;

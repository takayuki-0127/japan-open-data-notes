-- R3 部門グループ別の月次売上
SELECT c.cal_ym AS ym,
       CASE
         WHEN i.dept_id IN (1, 2) THEN '生鮮'
         WHEN i.dept_id IN (3, 4) THEN '加工食品'
         WHEN i.dept_id IN (5) THEN '日配'
         WHEN i.dept_id IN (6, 7) THEN '日用品'
         ELSE 'その他'
       END AS grp,
       SUM(x.amt) AS sales
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
JOIN item i ON i.item_id = x.item_id
GROUP BY c.cal_ym,
       CASE
         WHEN i.dept_id IN (1, 2) THEN '生鮮'
         WHEN i.dept_id IN (3, 4) THEN '加工食品'
         WHEN i.dept_id IN (5) THEN '日配'
         WHEN i.dept_id IN (6, 7) THEN '日用品'
         ELSE 'その他'
       END
ORDER BY 1, 2;

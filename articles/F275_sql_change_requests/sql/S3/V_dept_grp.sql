CREATE VIEW dept_grp AS
  SELECT d.dept_id,
         CASE
           WHEN d.dept_id IN (1, 2) THEN '生鮮'
           WHEN d.dept_id IN (3, 4) THEN '加工食品'
           WHEN d.dept_id IN (5) THEN '日配'
           WHEN d.dept_id IN (6, 7) THEN '日用品'
           ELSE 'その他'
         END AS grp
  FROM dept d;

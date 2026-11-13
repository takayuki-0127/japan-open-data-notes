-- 当時の部署名の月次実績を、新旧対応表（比率つき）で今の組織に組み替えて、2024年度の合計を出す（DuckDB）
-- 2025年4月以降は今の組織の名前で記録されているので、組み替えるのはそれより前だけ
SELECT m.new_dept,
       ROUND(SUM(r.sales * m.ratio), 1) AS fy2024
FROM monthly_by_dept r
JOIN dept_mapping m ON r.dept = m.old_dept
WHERE r.month >= DATE '2024-04-01' AND r.month < DATE '2025-04-01'
GROUP BY m.new_dept
ORDER BY m.new_dept;

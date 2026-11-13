-- T-SQL 版（SQL Server では動かしていない：未検証）
-- dept_mapping(old_dept, new_dept, ratio)：分割・移管は ratio で割り振る。1つの old_dept の ratio の合計は 1
SELECT m.new_dept,
       YEAR(DATEADD(MONTH, -3, r.month)) AS fiscal_year,   -- 4月始まりの年度
       ROUND(SUM(r.sales * m.ratio), 1) AS sales
FROM dbo.monthly_by_dept r
JOIN dbo.dept_mapping m ON r.dept = m.old_dept
WHERE r.month < '2025-04-01'
GROUP BY m.new_dept, YEAR(DATEADD(MONTH, -3, r.month))
UNION ALL
SELECT r.dept, YEAR(DATEADD(MONTH, -3, r.month)), ROUND(SUM(r.sales), 1)
FROM dbo.monthly_by_dept r
WHERE r.month >= '2025-04-01'
GROUP BY r.dept, YEAR(DATEADD(MONTH, -3, r.month));

-- 対応表の点検：old_dept ごとに ratio の合計が 1 になっているか
SELECT old_dept, SUM(ratio) AS total_ratio
FROM dbo.dept_mapping
GROUP BY old_dept
HAVING ABS(SUM(ratio) - 1) > 0.0001;

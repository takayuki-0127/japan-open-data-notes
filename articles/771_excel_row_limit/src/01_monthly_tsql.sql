-- T-SQL：未検証
SELECT FORMAT(sale_date, 'yyyy-MM') AS month,
       COUNT(*)    AS n_rows,
       SUM(CAST(amount AS bigint)) AS amount
FROM dbo.details
GROUP BY FORMAT(sale_date, 'yyyy-MM')
ORDER BY month;
-- 行数が Excel の上限を超えないかを先に確かめる
SELECT COUNT(*) AS n_rows, CASE WHEN COUNT(*) > 1048575 THEN 'Excel では切れる' ELSE '入る' END AS excel
FROM dbo.details;

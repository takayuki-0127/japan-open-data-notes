-- T-SQL：未検証
SELECT FORMAT(entry_date, 'yyyy-MM') AS month, COUNT(*) AS n_rows, SUM(amount) AS amount
FROM dbo.entries
GROUP BY FORMAT(entry_date, 'yyyy-MM')
ORDER BY month;

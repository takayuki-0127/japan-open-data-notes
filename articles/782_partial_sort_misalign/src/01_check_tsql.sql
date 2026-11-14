-- T-SQL：未検証
SELECT COUNT(*) AS n_rows,
       SUM(CASE WHEN s.amount <> o.amount THEN 1 ELSE 0 END) AS n_moved,
       SUM(ABS(s.amount - o.amount)) AS abs_gap,
       SUM(s.amount) - SUM(o.amount) AS total_gap
FROM dbo.sorted_table AS s
JOIN dbo.original AS o ON o.customer_id = s.customer_id;

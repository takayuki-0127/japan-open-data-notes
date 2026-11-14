-- T-SQL：未検証
SELECT month,
       SUM(CASE WHEN actual >= target THEN 1 ELSE 0 END)                                       AS achieved_exact,
       SUM(CASE WHEN ROUND(actual * 100.0 / target, 0) >= 100 THEN 1 ELSE 0 END)               AS achieved_round0,
       SUM(CASE WHEN ROUND(actual * 100.0 / target, 1) >= 100 THEN 1 ELSE 0 END)               AS achieved_round1,
       COUNT(*) AS stores
FROM dbo.results
GROUP BY month
ORDER BY month;

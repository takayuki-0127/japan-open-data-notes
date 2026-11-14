-- T-SQL：未検証
WITH q AS (
    SELECT DISTINCT month, PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY amount) OVER (PARTITION BY month) AS p99
    FROM dbo.receipts
), m AS (
    SELECT DISTINCT month, PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY amount) OVER (PARTITION BY month) AS median_all
    FROM dbo.receipts
)
SELECT r.month,
       AVG(CAST(r.amount AS float))                                                   AS mean_all,
       AVG(CASE WHEN r.is_business = 0 THEN CAST(r.amount AS float) END)              AS mean_personal,
       MAX(m.median_all)                                                              AS median_all,
       AVG(CASE WHEN r.amount > q.p99 THEN q.p99 ELSE CAST(r.amount AS float) END)    AS mean_capped
FROM dbo.receipts AS r
JOIN q ON q.month = r.month
JOIN m ON m.month = r.month
GROUP BY r.month
ORDER BY r.month;

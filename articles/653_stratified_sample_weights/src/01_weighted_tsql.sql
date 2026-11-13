-- T-SQL：未検証（SQL Server では動かしていない）
SELECT AVG(CAST(sales AS float))                                         AS sales_unweighted,
       SUM(sales / sample_rate) / SUM(1.0 / sample_rate)                 AS sales_weighted,
       AVG(cashless_rate)                                                AS cashless_unweighted,
       SUM(cashless_rate / sample_rate) / SUM(1.0 / sample_rate)         AS cashless_weighted
FROM dbo.sample_stores;

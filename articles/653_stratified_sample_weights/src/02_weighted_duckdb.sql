-- 抜き出した店の表から全体の平均を出す（DuckDB 版）。sample_stores(store_id, size_class, sales, cashless_rate, sample_rate)
SELECT AVG(sales)                                           AS sales_unweighted,
       SUM(sales / sample_rate) / SUM(1.0 / sample_rate)    AS sales_weighted,
       AVG(cashless_rate)                                   AS cashless_unweighted,
       SUM(cashless_rate / sample_rate) / SUM(1.0 / sample_rate) AS cashless_weighted
FROM sample_stores;

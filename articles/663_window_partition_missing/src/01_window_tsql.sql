-- T-SQL：未検証（SQL Server では動かしていない）
SELECT store_id, sale_date, sales,
  SUM(sales) OVER (PARTITION BY store_id ORDER BY sale_date ROWS UNBOUNDED PRECEDING)                AS cum_ok,
  SUM(sales) OVER (ORDER BY sale_date)                                                                AS cum_ng,   -- 既定は RANGE：同じ日の全店がまとめて足される
  AVG(CAST(sales AS float)) OVER (PARTITION BY store_id ORDER BY sale_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS ma7_ok,
  AVG(CAST(sales AS float)) OVER (ORDER BY store_id, sale_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)            AS ma7_ng,
  LAG(sales) OVER (PARTITION BY store_id ORDER BY sale_date)                                          AS prev_ok,
  LAG(sales) OVER (ORDER BY store_id, sale_date)                                                      AS prev_ng,
  RANK() OVER (PARTITION BY sale_date ORDER BY sales DESC)                                            AS rank_ok,
  RANK() OVER (ORDER BY sales DESC)                                                                   AS rank_ng
FROM dbo.daily
ORDER BY store_id, sale_date;

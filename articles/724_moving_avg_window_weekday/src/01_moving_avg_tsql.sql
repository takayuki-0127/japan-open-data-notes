-- T-SQL：未検証（SQL Server では動かしていない）
SELECT sales_date, sales,
       AVG(sales * 1.0) OVER (ORDER BY sales_date ROWS BETWEEN 2 PRECEDING AND CURRENT ROW)  AS ma3,
       AVG(sales * 1.0) OVER (ORDER BY sales_date ROWS BETWEEN 4 PRECEDING AND CURRENT ROW)  AS ma5,
       AVG(sales * 1.0) OVER (ORDER BY sales_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)  AS ma7,
       AVG(sales * 1.0) OVER (ORDER BY sales_date ROWS BETWEEN 13 PRECEDING AND CURRENT ROW) AS ma14,
       AVG(sales * 1.0) OVER (ORDER BY sales_date ROWS BETWEEN 27 PRECEDING AND CURRENT ROW) AS ma28
FROM daily_sales
ORDER BY sales_date;

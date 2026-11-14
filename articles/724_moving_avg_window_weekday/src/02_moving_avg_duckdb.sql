-- DuckDB で実行（1スレッド）。後ろ向き（その日までの k 日）の移動平均を5つの幅で出す
-- 行の数で数える（ROWS）ので、日付が抜けていない表であることが前提
SELECT sales_date, sales,
       AVG(sales) OVER (ORDER BY sales_date ROWS BETWEEN 2 PRECEDING AND CURRENT ROW)  AS ma3,
       AVG(sales) OVER (ORDER BY sales_date ROWS BETWEEN 4 PRECEDING AND CURRENT ROW)  AS ma5,
       AVG(sales) OVER (ORDER BY sales_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)  AS ma7,
       AVG(sales) OVER (ORDER BY sales_date ROWS BETWEEN 13 PRECEDING AND CURRENT ROW) AS ma14,
       AVG(sales) OVER (ORDER BY sales_date ROWS BETWEEN 27 PRECEDING AND CURRENT ROW) AS ma28,
       COUNT(*)   OVER (ORDER BY sales_date ROWS BETWEEN 27 PRECEDING AND CURRENT ROW) AS n28
FROM daily_sales
ORDER BY sales_date;

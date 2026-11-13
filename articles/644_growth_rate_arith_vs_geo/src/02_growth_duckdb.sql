-- DuckDB：年ごとの伸び率の算術平均と、年率（幾何平均）、最初と最後から出した年率
WITH g AS (
  SELECT store_id, yr, sales,
         sales / LAG(sales) OVER (PARTITION BY store_id ORDER BY yr) - 1 AS growth
  FROM annual_sales
)
SELECT store_id,
       AVG(growth)                   AS arith_mean,
       EXP(AVG(LN(1 + growth))) - 1  AS geo_mean,
       POWER(MAX(sales) FILTER (WHERE yr = 2025) / MAX(sales) FILTER (WHERE yr = 2020), 1.0 / 5) - 1 AS cagr
FROM g
GROUP BY store_id
ORDER BY store_id

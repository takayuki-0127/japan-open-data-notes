-- T-SQL：未検証（SQL Server では動かしていない）
-- 年ごとの伸び率の算術平均と、年率（幾何平均）
WITH g AS (
  SELECT store_id, yr, sales * 1.0 / LAG(sales) OVER (PARTITION BY store_id ORDER BY yr) - 1 AS growth
  FROM dbo.annual_sales
)
SELECT store_id,
       AVG(growth)                    AS arith_mean,
       EXP(AVG(LOG(1 + growth))) - 1  AS geo_mean        -- SQL Server の LOG は自然対数
FROM g WHERE growth IS NOT NULL
GROUP BY store_id;

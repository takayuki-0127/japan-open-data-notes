-- T-SQL：未検証（SQL Server では動かしていない）
-- 2025年の年間目標を、前年の月の比率で月に分ける
WITH ly AS (
  SELECT store_id, mon, sales,
         sales * 1.0 / SUM(sales) OVER (PARTITION BY store_id) AS share
  FROM dbo.monthly_sales WHERE yr = 2024
)
SELECT t.store_id, ly.mon,
       t.annual_target / 12.0          AS target_equal,
       t.annual_target * ly.share      AS target_ly
FROM dbo.annual_target t JOIN ly ON ly.store_id = t.store_id;

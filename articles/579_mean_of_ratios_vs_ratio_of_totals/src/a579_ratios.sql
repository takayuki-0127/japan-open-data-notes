-- 店ごとの購入率を「単純平均」「来店客数で重み付けた平均」「合計の比」で出す（DuckDB）
WITH y AS (
    SELECT 1 AS year, store, visitors_y1 AS visitors, buyers_y1 AS buyers FROM stores
    UNION ALL
    SELECT 2 AS year, store, visitors_y2, buyers_y2 FROM stores
)
SELECT year,
       AVG(buyers * 1.0 / visitors)                                   AS simple_mean,
       SUM(visitors * (buyers * 1.0 / visitors)) / SUM(visitors)       AS weighted_by_visitors,
       SUM(buyers) * 1.0 / SUM(visitors)                               AS ratio_of_totals,
       MEDIAN(buyers * 1.0 / visitors)                                 AS median_rate
FROM y
GROUP BY year
ORDER BY year;

-- 品目ごとに、売上の平均を3通りで出す（T-SQL、未検証）
-- stockout = その日の終わりに在庫が0だった日（bit）
SELECT
  item,
  COUNT(*)                                                     AS n_days,
  AVG(CAST(stockout AS float))                                 AS stockout_rate,
  AVG(CAST(sales AS float))                                    AS mean_all_days,
  AVG(CASE WHEN stockout = 1 THEN 0.0 ELSE CAST(sales AS float) END) AS mean_zero_on_stockout,
  AVG(CASE WHEN stockout = 0 THEN CAST(sales AS float) END)    AS mean_excl_stockout   -- NULL は AVG で除かれる
FROM dbo.daily
GROUP BY item
ORDER BY item;

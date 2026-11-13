-- 品目ごとに、売上の平均を3通りで出す（DuckDB）
-- stockout = その日の終わりに在庫が0だった日
SELECT
  item,
  COUNT(*)                                        AS n_days,
  AVG(CASE WHEN stockout THEN 1.0 ELSE 0.0 END)   AS stockout_rate,
  AVG(sales)                                      AS mean_all_days,      -- 欠品日もそのまま
  AVG(CASE WHEN stockout THEN 0 ELSE sales END)   AS mean_zero_on_stockout, -- 欠品日を0とみなす
  AVG(sales) FILTER (WHERE NOT stockout)          AS mean_excl_stockout  -- 欠品日を欠測として除く
FROM daily
GROUP BY item
ORDER BY item;

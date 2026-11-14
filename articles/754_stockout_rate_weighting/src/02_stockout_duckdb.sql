-- 欠品率の3つの数え方（DuckDB 版）
-- inventory(store_id, sku, d DATE, stockout INTEGER（欠品なら1）), skus(sku, daily_rate（1日に売れる数の見込み）)
SELECT i.store_id,
       AVG(i.stockout) * 100                                             AS rate_sku_days,        -- A SKU×日の数で割る
       SUM(i.stockout * s.daily_rate) / SUM(s.daily_rate) * 100          AS rate_sales_weighted,  -- B 売上の重み
       COUNT(DISTINCT CASE WHEN i.stockout = 1 THEN i.sku END) * 100.0
         / COUNT(DISTINCT i.sku)                                         AS rate_any_sku          -- C 1日でも欠品した SKU の割合
FROM inventory i
JOIN skus s USING (sku)
GROUP BY i.store_id
ORDER BY i.store_id;

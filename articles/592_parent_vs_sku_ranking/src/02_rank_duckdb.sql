-- 親品番（色・サイズをまとめた単位）で数量を足して順位を付ける（DuckDB）
-- 正しい方法：商品マスタで SKU → 親品番 をひく
-- よくある近道：SKU コードの先頭6文字を親品番とみなす
WITH by_master AS (
  SELECT m.parent, SUM(s.qty) AS qty
  FROM sales s JOIN sku_master m ON m.sku = s.sku
  GROUP BY m.parent
), by_prefix AS (
  SELECT LEFT(s.sku, 6) AS parent, SUM(s.qty) AS qty
  FROM sales s
  GROUP BY LEFT(s.sku, 6)
)
SELECT 'master' AS method, parent, qty, RANK() OVER (ORDER BY qty DESC) AS rnk FROM by_master
UNION ALL
SELECT 'prefix6', parent, qty, RANK() OVER (ORDER BY qty DESC) FROM by_prefix
ORDER BY method, rnk, parent;

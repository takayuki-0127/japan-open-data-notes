-- 親品番で数量を足して順位を付ける（T-SQL、未検証）
WITH by_master AS (
  SELECT m.parent, SUM(s.qty) AS qty
  FROM dbo.sales AS s
  JOIN dbo.sku_master AS m ON m.sku = s.sku
  GROUP BY m.parent
), by_prefix AS (
  SELECT LEFT(s.sku, 6) AS parent, SUM(s.qty) AS qty     -- 親品番の桁数が違う商品があると、別の商品と混ざる
  FROM dbo.sales AS s
  GROUP BY LEFT(s.sku, 6)
)
SELECT 'master' AS method, parent, qty, RANK() OVER (ORDER BY qty DESC) AS rnk FROM by_master
UNION ALL
SELECT 'prefix6', parent, qty, RANK() OVER (ORDER BY qty DESC) FROM by_prefix
ORDER BY method, rnk, parent;

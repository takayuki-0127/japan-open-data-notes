-- 名前を20文字で切ると同じ名前がいくつできるか（DuckDB 版。DuckDB の VARCHAR には長さの上限がないので LEFT で再現）
-- products(product_id, name, sales)
SELECT COUNT(DISTINCT LEFT(name, 20)) AS n_names FROM products;
-- 入れる前に、上限を超える名前を数える
SELECT COUNT(*) AS too_long FROM products WHERE length(name) > 20;
-- 切ったあとの名前で、ほかの品目と重なるもの
SELECT LEFT(name, 20) AS short_name, COUNT(*) AS n_products, SUM(sales) AS sales
FROM products
GROUP BY LEFT(name, 20)
HAVING COUNT(*) > 1
ORDER BY n_products DESC;

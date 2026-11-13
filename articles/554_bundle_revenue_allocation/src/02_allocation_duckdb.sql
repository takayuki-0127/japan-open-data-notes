-- セット商品の売上を構成品に割り振る（DuckDB 版）：単品価格の比で按分
-- set_sales(sale_id, set_id, qty, amount)、set_components(set_id, item_id, units)、items(item_id, list_price, unit_cost)
WITH comp AS (
  SELECT c.set_id, c.item_id, c.units, i.list_price * c.units AS list_value,
         SUM(i.list_price * c.units) OVER (PARTITION BY c.set_id) AS set_list_value
  FROM set_components AS c JOIN items AS i ON i.item_id = c.item_id)
SELECT comp.item_id, SUM(s.amount * comp.list_value / comp.set_list_value) AS allocated_sales
FROM set_sales AS s JOIN comp ON comp.set_id = s.set_id
GROUP BY comp.item_id
ORDER BY comp.item_id;

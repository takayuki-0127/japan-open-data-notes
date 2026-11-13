-- セット商品の売上を構成品に割り振る（T-SQL 版。SQL Server では動かしていない：未検証）
-- 単品価格の比で按分。原価の比なら list_price を unit_cost に、均等なら 1.0 / COUNT(*) OVER (PARTITION BY set_id) に置き換える
WITH comp AS (
  SELECT c.set_id, c.item_id, c.units, CAST(i.list_price * c.units AS DECIMAL(18, 4)) AS list_value,
         SUM(CAST(i.list_price * c.units AS DECIMAL(18, 4))) OVER (PARTITION BY c.set_id) AS set_list_value
  FROM dbo.set_components AS c JOIN dbo.items AS i ON i.item_id = c.item_id)
SELECT comp.item_id, SUM(s.amount * comp.list_value / comp.set_list_value) AS allocated_sales
FROM dbo.set_sales AS s JOIN comp ON comp.set_id = s.set_id
GROUP BY comp.item_id;

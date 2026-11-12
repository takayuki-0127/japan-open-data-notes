-- 店ごとの「販売数の上位3件」（T-SQL。SQL Server 本体では動かしていません：未検証）
-- store_sales(store_id, product_id, units, amount)

-- ① ROW_NUMBER：必ず3件。同点のどれが入るかは決まっていない
SELECT store_id, product_id, units
FROM (SELECT *, ROW_NUMBER() OVER (PARTITION BY store_id ORDER BY units DESC) AS rn
      FROM store_sales) AS t
WHERE rn <= 3;

-- ② RANK：3位に同点があれば全部返す（TOP (3) WITH TIES と同じ件数になる）
SELECT store_id, product_id, units
FROM (SELECT *, RANK() OVER (PARTITION BY store_id ORDER BY units DESC) AS rk
      FROM store_sales) AS t
WHERE rk <= 3;

-- ②' 店ごとに TOP (3) WITH TIES
SELECT s.store_id, x.product_id, x.units
FROM (SELECT DISTINCT store_id FROM store_sales) AS s
CROSS APPLY (SELECT TOP (3) WITH TIES product_id, units
             FROM store_sales AS t WHERE t.store_id = s.store_id
             ORDER BY units DESC) AS x;

-- ③ DENSE_RANK：販売数の「上位3つの値」に入る商品を全部返す
SELECT store_id, product_id, units
FROM (SELECT *, DENSE_RANK() OVER (PARTITION BY store_id ORDER BY units DESC) AS dr
      FROM store_sales) AS t
WHERE dr <= 3;

-- ④ 必ず3件で、毎回同じ顔ぶれにする：同点のときの決まりを ORDER BY に書く
SELECT store_id, product_id, units
FROM (SELECT *, ROW_NUMBER() OVER (PARTITION BY store_id ORDER BY units DESC, product_id) AS rn
      FROM store_sales) AS t
WHERE rn <= 3;

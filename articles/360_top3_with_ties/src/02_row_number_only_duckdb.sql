-- ROW_NUMBER だけを単独で実行する版（同点の順を決めていない）
SELECT store_id, product_id
FROM (SELECT store_id, product_id,
             ROW_NUMBER() OVER (PARTITION BY store_id ORDER BY units DESC) AS rn
      FROM store_sales) AS t
WHERE rn <= 3;

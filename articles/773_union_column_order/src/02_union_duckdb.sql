-- 列の位置でつなぐ（まちがい）：store_b は amount と qty の順番が逆
CREATE OR REPLACE TABLE by_position AS
SELECT * FROM store_a
UNION ALL
SELECT * FROM store_b;

-- 列名を書いてつなぐ（正しい）
CREATE OR REPLACE TABLE by_listed AS
SELECT sale_date, store, item, qty, amount FROM store_a
UNION ALL
SELECT sale_date, store, item, qty, amount FROM store_b;

-- 列名で合わせてつなぐ（DuckDB の UNION ALL BY NAME）
CREATE OR REPLACE TABLE by_name AS
SELECT * FROM store_a
UNION ALL BY NAME
SELECT * FROM store_b;

SELECT 'by_position' AS how, store, SUM(qty) AS qty, SUM(amount) AS amount FROM by_position GROUP BY store
UNION ALL
SELECT 'by_listed', store, SUM(qty), SUM(amount) FROM by_listed GROUP BY store
UNION ALL
SELECT 'by_name', store, SUM(qty), SUM(amount) FROM by_name GROUP BY store
ORDER BY how, store;

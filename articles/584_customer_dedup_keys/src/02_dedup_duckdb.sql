-- 電話番号だけで寄せたときの顧客数（DuckDB）
-- 数字以外（ハイフンなど）を消し、全角数字を半角に直してから比べる
-- 電話が空の行は、ID ごとに別の顧客として数える
WITH k AS (
  SELECT
    customer_id,
    NULLIF(regexp_replace(COALESCE(phone, ''), '[^0-9０-９]', '', 'g'), '') AS p0
  FROM customers
), k2 AS (
  SELECT customer_id,
         translate(p0, '０１２３４５６７８９', '0123456789') AS phone_key
  FROM k
)
SELECT COUNT(DISTINCT COALESCE(phone_key, 'id:' || customer_id)) AS customers_by_phone
FROM k2;

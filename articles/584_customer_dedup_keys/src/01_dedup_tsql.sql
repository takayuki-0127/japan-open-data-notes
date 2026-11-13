-- 電話番号だけで寄せたときの顧客数（T-SQL、未検証）
-- 全角数字を半角に直し、ハイフン（半角・全角）を消してから比べる。電話が空の行は ID ごとに数える
WITH k AS (
  SELECT
    customer_id,
    NULLIF(
      REPLACE(REPLACE(TRANSLATE(phone, N'０１２３４５６７８９', N'0123456789'), N'-', N''), N'－', N''),
      N'') AS phone_key
  FROM dbo.customers
)
SELECT COUNT(DISTINCT COALESCE(phone_key, N'id:' + customer_id)) AS customers_by_phone
FROM k;

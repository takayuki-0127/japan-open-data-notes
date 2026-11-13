-- T-SQL 版（SQL Server では動かしていない：未検証）
-- ① 同じ金額の請求と入金を、日付の順に番号を振ってつなぐ
WITH i AS (
  SELECT inv_id, amount, due_date,
         ROW_NUMBER() OVER (PARTITION BY amount ORDER BY due_date, inv_id) AS rn
  FROM dbo.invoices WHERE status = N'open'
), p AS (
  SELECT pay_id, amount, pay_date,
         ROW_NUMBER() OVER (PARTITION BY amount ORDER BY pay_date, pay_id) AS rn
  FROM dbo.payments WHERE matched_inv_id IS NULL
)
SELECT p.pay_id, i.inv_id
FROM p LEFT JOIN i ON i.amount = p.amount AND i.rn = p.rn;

-- ③ 名義を正規化した列（payer_norm）と取引先のカナ（kana）、金額または金額＋手数料でつなぐ
WITH c AS (
  SELECT p.pay_id, v.inv_id,
         ROW_NUMBER() OVER (PARTITION BY p.pay_id
                            ORDER BY CASE WHEN v.amount = p.amount THEN 0 ELSE 1 END, v.due_date, v.inv_id) AS k
  FROM dbo.payments p
  JOIN dbo.customers cu ON cu.kana = p.payer_norm
  JOIN dbo.invoices v ON v.cust_id = cu.cust_id AND v.status = N'open'
   AND v.amount IN (p.amount, p.amount + 440, p.amount + 660, p.amount + 770)
)
SELECT pay_id, inv_id FROM c WHERE k = 1;
-- 注意：この形は1件の請求に2件の入金が当たることを止めない。実際は1件ずつ当てて請求を閉じる処理が要る

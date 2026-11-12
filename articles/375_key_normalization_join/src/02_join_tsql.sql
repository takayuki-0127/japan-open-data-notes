-- 375：T-SQL での書き方（SQL Server 本体では動かしていない＝未検証）
-- (a) 照合順序に任せる：Japanese_CI_AS は、大文字小文字（CI）、全角半角（WS なし）、ひらがなカタカナ（KS なし）を区別しない。
--     = の比べでは、後ろの半角の空白も無視される。前の空白、全角の空白、間の空白、（株）と株式会社の違いは残る
SELECT i.invoice_no, m.customer_id
FROM invoices AS i
LEFT JOIN customers AS m
       ON m.customer_name = i.customer_name COLLATE Japanese_CI_AS;

-- (b) キーを作ってからつなぐ：空白（半角・全角）を取り、（株）・㈱ を株式会社にそろえる
--     TRANSLATE と REPLACE は SQL Server 2017 以降
WITH inv AS (
  SELECT invoice_no,
         REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(customer_name, N'　', N''), N' ', N''),
                 N'（株）', N'株式会社'), N'(株)', N'株式会社'), N'㈱', N'株式会社') AS k
  FROM invoices),
mst AS (
  SELECT customer_id,
         REPLACE(REPLACE(customer_name, N'　', N''), N' ', N'') AS k
  FROM customers)
SELECT i.invoice_no, m.customer_id,
       COUNT(*) OVER (PARTITION BY i.invoice_no) AS matches   -- 2以上なら、別々の取引先が同じキーになっている
FROM inv AS i
LEFT JOIN mst AS m ON m.k = i.k COLLATE Japanese_CI_AS;

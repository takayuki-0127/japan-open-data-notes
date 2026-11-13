-- T-SQL 版（SQL Server では動かしていない：未検証）
-- 売った時点の住所で数える。valid_to は次の住所の開始日（最後の住所は '9999-12-31'）
SELECT a.region, YEAR(o.ordered_on) AS yr, SUM(o.amount) AS sales
FROM dbo.orders o
JOIN dbo.address_history a
  ON o.customer_id = a.customer_id
 AND a.valid_from <= o.ordered_on AND o.ordered_on < a.valid_to
GROUP BY a.region, YEAR(o.ordered_on);

-- 履歴の点検：同じ顧客の有効期間が重なっていないか（重なると注文が二重に数えられる）
SELECT a.customer_id, COUNT(*) AS overlaps
FROM dbo.address_history a
JOIN dbo.address_history b
  ON a.customer_id = b.customer_id AND a.valid_from < b.valid_from AND b.valid_from < a.valid_to
GROUP BY a.customer_id;

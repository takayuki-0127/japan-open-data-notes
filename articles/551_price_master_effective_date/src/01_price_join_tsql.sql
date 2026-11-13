-- 明細に単価を付ける（T-SQL 版。SQL Server では動かしていない：未検証）
-- price_master(item_id, price, valid_from DATE, valid_to DATE NULL)。valid_to は次の単価の開始日（その日を含まない）
-- J0 正しい結合
SELECT d.line_id, d.item_id, d.sold_on, d.qty, m.price, d.qty * m.price AS amount
FROM dbo.sales_lines AS d
JOIN dbo.price_master AS m
  ON m.item_id = d.item_id
 AND d.sold_on >= m.valid_from
 AND (m.valid_to IS NULL OR d.sold_on < m.valid_to);

-- J1 今の単価で結ぶ（よくあるずれ）
SELECT d.line_id, d.qty * m.price AS amount
FROM dbo.sales_lines AS d
JOIN dbo.price_master AS m ON m.item_id = d.item_id AND m.valid_to IS NULL;

-- J3 BETWEEN で両端を含める（切り替え日の明細が2行になる）
SELECT d.line_id, d.qty * m.price AS amount
FROM dbo.sales_lines AS d
JOIN dbo.price_master AS m
  ON m.item_id = d.item_id
 AND d.sold_on BETWEEN m.valid_from AND ISNULL(m.valid_to, '9999-12-31');

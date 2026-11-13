-- 明細に単価を付ける（DuckDB 版）。price_master(item_id, price, valid_from, valid_to)、valid_to は次の単価の開始日（その日を含まない）、今の単価は NULL
-- J0 正しい結合：明細の日付が valid_from 以上、valid_to より前
SELECT d.line_id, d.item_id, d.sold_on, d.qty, m.price, d.qty * m.price AS amount
FROM sales_lines AS d
JOIN price_master AS m
  ON m.item_id = d.item_id
 AND d.sold_on >= m.valid_from
 AND (m.valid_to IS NULL OR d.sold_on < m.valid_to);

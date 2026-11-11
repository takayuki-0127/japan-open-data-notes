CREATE VIEW cust AS
  SELECT r.date_key, r.store_id,
         r.receipt_id AS cust_key
  FROM receipt r
  WHERE EXISTS (SELECT 1 FROM line_ok o WHERE o.receipt_id = r.receipt_id);

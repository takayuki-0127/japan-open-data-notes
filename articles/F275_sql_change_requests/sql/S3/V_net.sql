CREATE VIEW net AS
  SELECT o.date_key AS d, o.store_id, o.item_id, o.amount_incl * o.amt_factor AS amt
  FROM line_ok o
  UNION ALL
  SELECT r.return_date_key AS d, o.store_id, o.item_id, -r.amount_incl * o.amt_factor AS amt
  FROM returns_line r
  JOIN line_ok o ON o.receipt_id = r.receipt_id AND o.line_no = r.line_no;

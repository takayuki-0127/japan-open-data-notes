CREATE VIEW comp_store AS
  SELECT s.store_id, m.mi
  FROM store s
  JOIN mon om ON om.date_key = s.open_date_key
  CROSS JOIN (SELECT DISTINCT mi FROM mon) m
  WHERE om.mi <= m.mi - 13;

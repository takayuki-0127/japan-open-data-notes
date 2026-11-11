CREATE VIEW mon AS
  SELECT c.date_key, c.cal_ym AS ym, c.cal_mi AS mi
  FROM calendar c;

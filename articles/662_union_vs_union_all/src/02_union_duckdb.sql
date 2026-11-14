-- 2つの店の明細表をまとめる4通り（DuckDB 版）
-- sales_a / sales_b (store_id, receipt_no, line_no, sold_at, item, qty, amount)
-- U1 店と レシートの列を落として UNION
SELECT COUNT(*) AS n_rows, SUM(amount) AS amount FROM (
  SELECT sold_at, item, qty, amount FROM sales_a
  UNION
  SELECT sold_at, item, qty, amount FROM sales_b) AS t;
-- U2 店の列は残して UNION（レシートの列は落とす）
SELECT COUNT(*) AS n_rows, SUM(amount) AS amount FROM (
  SELECT store_id, sold_at, item, qty, amount FROM sales_a
  UNION
  SELECT store_id, sold_at, item, qty, amount FROM sales_b) AS t;
-- U3 UNION ALL（二重に取り込んだ日もそのまま）
SELECT COUNT(*) AS n_rows, SUM(amount) AS amount FROM (
  SELECT store_id, receipt_no, line_no, sold_at, item, qty, amount FROM sales_a
  UNION ALL
  SELECT store_id, receipt_no, line_no, sold_at, item, qty, amount FROM sales_b) AS t;
-- U4 UNION ALL のあと、明細のキー（店・レシート・行）で1行に絞る
SELECT COUNT(*) AS n_rows, SUM(amount) AS amount FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY store_id, receipt_no, line_no ORDER BY sold_at) AS rn
  FROM (SELECT store_id, receipt_no, line_no, sold_at, item, qty, amount FROM sales_a
        UNION ALL
        SELECT store_id, receipt_no, line_no, sold_at, item, qty, amount FROM sales_b) AS u) AS t
WHERE rn = 1;

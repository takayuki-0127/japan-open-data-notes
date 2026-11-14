-- T-SQL：未検証（SQL Server では動かしていない）
-- U1 店とレシートの列を落として UNION（同じ内容の明細が1行にまとまる）
SELECT COUNT(*) AS n_rows, SUM(amount) AS amount FROM (
  SELECT sold_at, item, qty, amount FROM dbo.sales_a
  UNION
  SELECT sold_at, item, qty, amount FROM dbo.sales_b) AS t;
-- U3 UNION ALL（二重に取り込んだ日も残る）
SELECT COUNT(*) AS n_rows, SUM(amount) AS amount FROM (
  SELECT store_id, receipt_no, line_no, sold_at, item, qty, amount FROM dbo.sales_a
  UNION ALL
  SELECT store_id, receipt_no, line_no, sold_at, item, qty, amount FROM dbo.sales_b) AS t;
-- U4 UNION ALL のあと、明細のキーで1行に絞る
WITH u AS (
  SELECT store_id, receipt_no, line_no, sold_at, item, qty, amount FROM dbo.sales_a
  UNION ALL
  SELECT store_id, receipt_no, line_no, sold_at, item, qty, amount FROM dbo.sales_b),
r AS (SELECT *, ROW_NUMBER() OVER (PARTITION BY store_id, receipt_no, line_no ORDER BY sold_at) AS rn FROM u)
SELECT COUNT(*) AS n_rows, SUM(amount) AS amount FROM r WHERE rn = 1;

-- 長い番号の列を、文字・整数・小数（DOUBLE）で読んだときの違いを数える（DuckDB）
-- ? には CSV のパスを入れる
SELECT
  COUNT(*)                                     AS n_rows,
  COUNT(DISTINCT order_no_text)                AS distinct_text,
  COUNT(DISTINCT order_no_bigint)              AS distinct_bigint,
  COUNT(DISTINCT order_no_double)              AS distinct_double,
  SUM(CASE WHEN CAST(order_no_double AS HUGEINT) <> order_no_bigint THEN 1 ELSE 0 END) AS changed_by_double
FROM (
  SELECT order_no                    AS order_no_text,
         CAST(order_no AS BIGINT)    AS order_no_bigint,
         CAST(order_no AS DOUBLE)    AS order_no_double
  FROM read_csv(?, columns = {'order_no': 'VARCHAR', 'amount': 'BIGINT'}, header = true)
);

-- T-SQL：未検証
-- 長い番号は文字（VARCHAR）か BIGINT（19桁まで）で持つ。FLOAT にすると15〜17桁目から先が変わる
SELECT
  COUNT(*)                                          AS n_rows,
  COUNT(DISTINCT order_no)                          AS distinct_text,
  COUNT(DISTINCT CAST(order_no AS BIGINT))          AS distinct_bigint,
  COUNT(DISTINCT CAST(order_no AS FLOAT))           AS distinct_float
FROM dbo.orders_raw;   -- order_no は VARCHAR(20) で取り込んだもの

-- 構成比を整数の%にして、合計を必ず100にする（最大剰余法、DuckDB 版）
-- shares(table_id, item, value)。表ごとに、切り捨てた%の合計の不足分を、小数部分の大きい項目から1ずつ足す
WITH s AS (
  SELECT table_id, item, value,
         100.0 * value / SUM(value) OVER (PARTITION BY table_id) AS pct
  FROM shares),
f AS (
  SELECT *, FLOOR(pct) AS base, pct - FLOOR(pct) AS rem,
         100 - SUM(FLOOR(pct)) OVER (PARTITION BY table_id) AS short
  FROM s),
r AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY table_id ORDER BY rem DESC, item) AS rk
  FROM f)
SELECT table_id, item, pct,
       ROUND(pct) AS pct_round,                                   -- ふつうの四捨五入（合計が100にならないことがある）
       base + CASE WHEN rk <= short THEN 1 ELSE 0 END AS pct_lr   -- 最大剰余法
FROM r
ORDER BY table_id, item;

-- 納期の遵守を3通りの約束日で判定する（DuckDB で実行）
-- orders(order_id, ordered, promise_initial, shipped)、changes(order_id, seq, changed_on, new_promise, kind)
-- A：当初の約束日、B：最後に変えた日、C：出荷の3日前以内の変更を除いた最後の日
WITH c AS (
  SELECT ch.*, o.shipped,
         date_diff('day', CAST(ch.changed_on AS DATE), CAST(o.shipped AS DATE)) AS days_before_ship
  FROM changes AS ch JOIN orders AS o USING (order_id)),
last_all AS (
  SELECT order_id, new_promise FROM c
  QUALIFY row_number() OVER (PARTITION BY order_id ORDER BY changed_on DESC, seq DESC) = 1),
last_ex AS (
  SELECT order_id, new_promise FROM c WHERE days_before_ship > 3
  QUALIFY row_number() OVER (PARTITION BY order_id ORDER BY changed_on DESC, seq DESC) = 1)
SELECT o.order_id,
       o.shipped <= o.promise_initial                             AS ok_a,
       o.shipped <= COALESCE(la.new_promise, o.promise_initial)   AS ok_b,
       o.shipped <= COALESCE(le.new_promise, o.promise_initial)   AS ok_c
FROM orders AS o
LEFT JOIN last_all AS la USING (order_id)
LEFT JOIN last_ex  AS le USING (order_id)
ORDER BY o.order_id;

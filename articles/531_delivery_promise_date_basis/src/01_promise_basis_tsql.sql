-- 納期の遵守を3通りの約束日で判定する（T-SQL 版、SQL Server では未検証）
-- dbo.orders(order_id, ordered, promise_initial, shipped)、dbo.changes(order_id, seq, changed_on, new_promise, kind)
WITH c AS (
  SELECT ch.order_id, ch.seq, ch.changed_on, ch.new_promise,
         DATEDIFF(day, ch.changed_on, o.shipped) AS days_before_ship
  FROM dbo.changes AS ch JOIN dbo.orders AS o ON o.order_id = ch.order_id),
ranked AS (
  SELECT order_id, new_promise, days_before_ship,
         ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY changed_on DESC, seq DESC) AS rn_all,
         ROW_NUMBER() OVER (PARTITION BY order_id, CASE WHEN days_before_ship > 3 THEN 1 ELSE 0 END
                            ORDER BY changed_on DESC, seq DESC) AS rn_grp
  FROM c)
SELECT o.order_id,
       CASE WHEN o.shipped <= o.promise_initial THEN 1 ELSE 0 END                              AS ok_a,
       CASE WHEN o.shipped <= COALESCE(la.new_promise, o.promise_initial) THEN 1 ELSE 0 END    AS ok_b,
       CASE WHEN o.shipped <= COALESCE(le.new_promise, o.promise_initial) THEN 1 ELSE 0 END    AS ok_c
FROM dbo.orders AS o
LEFT JOIN ranked AS la ON la.order_id = o.order_id AND la.rn_all = 1
LEFT JOIN ranked AS le ON le.order_id = o.order_id AND le.days_before_ship > 3 AND le.rn_grp = 1
ORDER BY o.order_id;

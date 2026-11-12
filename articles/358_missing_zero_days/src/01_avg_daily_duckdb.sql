-- 店ごとの「1日あたりの売上」を3通りで出す（DuckDB で実行した版）
-- sales(store_id, d, amount)：売上のあった日だけ行がある　　store_days(store_id, d)：店が開いていた日
WITH a AS (            -- A：売上の表だけで平均（売上0の日が入らない）
  SELECT store_id, AVG(amount) AS avg_a FROM sales GROUP BY store_id
), b AS (              -- B：全部の日を並べて0で埋める（休みの日まで0として入る）
  SELECT st.store_id, AVG(COALESCE(s.amount, 0)) AS avg_b
  FROM (SELECT DISTINCT store_id FROM store_days) AS st
  CROSS JOIN (SELECT DISTINCT d FROM store_days) AS c
  LEFT JOIN sales AS s ON s.store_id = st.store_id AND s.d = c.d
  GROUP BY st.store_id
), c AS (              -- C：開いていた日だけを並べて0で埋める
  SELECT sd.store_id, AVG(COALESCE(s.amount, 0)) AS avg_c
  FROM store_days AS sd
  LEFT JOIN sales AS s ON s.store_id = sd.store_id AND s.d = sd.d
  GROUP BY sd.store_id
)
SELECT a.store_id, a.avg_a, b.avg_b, c.avg_c
FROM a JOIN b USING (store_id) JOIN c USING (store_id)
ORDER BY a.store_id;

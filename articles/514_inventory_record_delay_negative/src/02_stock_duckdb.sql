-- 日次の締めの在庫：d日目までに起きて、d日目24時＋{LAG}時間までに記録されたものを積み上げる（DuckDB で実行）
-- {LAG}=0 のときは「記録時刻で積み上げた在庫」と同じになる
WITH days AS (SELECT range AS d FROM range(1, {DAYS} + 1)),
first_day AS (
  SELECT item, qty,
         GREATEST(CAST(ceil(event_h / 24) AS INTEGER), CAST(ceil((record_h - {LAG}) / 24) AS INTEGER), 1) AS fd
  FROM rec
)
SELECT i.item, days.d,
       i.init + COALESCE(SUM(f.qty), 0) AS stock
FROM init_stock AS i
CROSS JOIN days
LEFT JOIN first_day AS f ON f.item = i.item AND f.fd <= days.d
GROUP BY i.item, days.d, i.init
ORDER BY i.item, days.d;

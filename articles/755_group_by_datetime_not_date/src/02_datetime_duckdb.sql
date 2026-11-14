-- 時刻つきの日時のまま日別に集計すると何が起きるか（DuckDB 版）
-- orders(order_id, channel, ordered_at TIMESTAMP, amount)  店舗の注文は日付だけ（00:00:00）、EC の注文は秒まで
-- A 日時のまま GROUP BY（「日別」のつもり）
SELECT ordered_at, COUNT(*) AS orders, SUM(amount) AS amount
FROM orders GROUP BY ordered_at ORDER BY ordered_at;
-- B 日付のカレンダー表と「=」で結合（00:00:00 ちょうどの注文しか結びつかない）
SELECT c.d, COUNT(o.order_id) AS orders, COALESCE(SUM(o.amount), 0) AS amount
FROM calendar c LEFT JOIN orders o ON o.ordered_at = c.d
GROUP BY c.d ORDER BY c.d;
-- C 日付に直してから GROUP BY（正しい）
SELECT CAST(ordered_at AS DATE) AS d, COUNT(*) AS orders, SUM(amount) AS amount
FROM orders GROUP BY CAST(ordered_at AS DATE) ORDER BY d;
-- D 文字の先頭10桁で GROUP BY（YYYY-MM-DD の形なら C と同じ）
SELECT LEFT(CAST(ordered_at AS VARCHAR), 10) AS d, COUNT(*) AS orders, SUM(amount) AS amount
FROM orders GROUP BY LEFT(CAST(ordered_at AS VARCHAR), 10) ORDER BY d;
-- E 期間で結合（d 以上、d+1 未満）。カレンダーと結ぶならこの形
SELECT c.d, COUNT(o.order_id) AS orders, COALESCE(SUM(o.amount), 0) AS amount
FROM calendar c LEFT JOIN orders o ON o.ordered_at >= c.d AND o.ordered_at < c.d + INTERVAL 1 DAY
GROUP BY c.d ORDER BY c.d;

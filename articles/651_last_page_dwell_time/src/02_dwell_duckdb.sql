-- 1ページごとの滞在時間を「次のページを開いた時刻との差」で出す（DuckDB 版）
-- pageviews(session_id, seq, page, ts)
SELECT session_id, seq, page, ts,
       epoch(LEAD(ts) OVER (PARTITION BY session_id ORDER BY seq)) - epoch(ts) AS dwell_sec  -- 最後のページは NULL
FROM pageviews
ORDER BY session_id, seq;
-- ページごとの平均：NULL を除く（最後のページを落とす）／NULL を0とみなす
SELECT page,
       AVG(dwell_sec)               AS avg_drop_last,
       AVG(COALESCE(dwell_sec, 0))  AS avg_last_as_zero,
       COUNT(*)                     AS views,
       SUM(CASE WHEN dwell_sec IS NULL THEN 1 ELSE 0 END) AS exits
FROM dwell
GROUP BY page
ORDER BY page;

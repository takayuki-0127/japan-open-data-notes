-- 月ごとの件数を3通りで出す（DuckDB 版）。applications(app_id, created_at)
SELECT strftime(created_at, '%Y-%m')          AS ym,
       COUNT(*)                                AS n_rows,          -- 本当に残っている件数
       MAX(app_id) - MIN(app_id) + 1           AS n_by_id_range,   -- 連番の幅で数える
       MAX(app_id)                             AS max_id
FROM applications
GROUP BY ym
ORDER BY ym;
-- 欠番の場所：前の行との差が2以上のところ
SELECT app_id, prev_id, app_id - prev_id - 1 AS missing
FROM (SELECT app_id, LAG(app_id) OVER (ORDER BY app_id) AS prev_id FROM applications) AS t
WHERE app_id - prev_id > 1
ORDER BY missing DESC;

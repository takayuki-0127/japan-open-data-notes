-- 在庫回転日数を3通りの平均在庫で出す（DuckDB で実行）
-- inv(date, inbound, shipped, inv_end)：日ごとの入荷・払出し・日末の在庫。期は 2025-01-01〜2025-12-31
WITH y AS (SELECT * FROM inv WHERE date BETWEEN DATE '2025-01-01' AND DATE '2025-12-31'),
     per_day AS (SELECT SUM(shipped) / COUNT(*) AS v FROM y),
     opening AS (SELECT inv_end AS v FROM inv WHERE date = DATE '2024-12-31'),
     closing AS (SELECT inv_end AS v FROM y WHERE date = DATE '2025-12-31'),
     month_end AS (SELECT inv_end AS v FROM y WHERE date = last_day(date)
                   UNION ALL SELECT v FROM opening)
SELECT ((SELECT v FROM opening) + (SELECT v FROM closing)) / 2 / (SELECT v FROM per_day) AS days_open_close,
       (SELECT AVG(v) FROM month_end) / (SELECT v FROM per_day)                          AS days_month_end,
       (SELECT AVG(inv_end) FROM y) / (SELECT v FROM per_day)                            AS days_daily;

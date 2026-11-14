-- 「時.分」で書かれた作業時間を分に直して合計する（DuckDB）
-- style = 'hmm' は「1.30＝1時間30分」、style = 'dec' は「1.5＝1.5時間」
SELECT w.staff_id,
       SUM(CAST(w.hours_text AS DOUBLE))                           AS naive_hours,   -- そのまま足す
       SUM(CASE WHEN s.style = 'hmm'
                THEN CAST(split_part(w.hours_text, '.', 1) AS INTEGER) * 60
                   + CAST(rpad(split_part(w.hours_text, '.', 2), 2, '0') AS INTEGER)
                ELSE round(CAST(w.hours_text AS DOUBLE) * 60) END) / 60.0 AS true_hours
FROM work_log AS w
JOIN staff AS s ON s.staff_id = w.staff_id
GROUP BY w.staff_id
ORDER BY w.staff_id;

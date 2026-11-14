-- T-SQL：未検証
SELECT w.staff_id,
       SUM(CAST(w.hours_text AS float))                            AS naive_hours,
       SUM(CASE WHEN s.style = 'hmm'
                THEN CAST(LEFT(w.hours_text, CHARINDEX('.', w.hours_text + '.') - 1) AS int) * 60
                   + CAST(LEFT(SUBSTRING(w.hours_text, CHARINDEX('.', w.hours_text + '.') + 1, 2) + '00', 2) AS int)
                ELSE ROUND(CAST(w.hours_text AS float) * 60, 0) END) / 60.0 AS true_hours
FROM dbo.work_log AS w
JOIN dbo.staff AS s ON s.staff_id = w.staff_id
GROUP BY w.staff_id
ORDER BY w.staff_id;

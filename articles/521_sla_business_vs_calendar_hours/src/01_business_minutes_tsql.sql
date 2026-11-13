-- T-SQL 版（SQL Server では動かしていない：未検証）
-- dbo.cal(d date, biz bit, mins int, cum_before int)：営業日のカレンダー表。営業時間は 9:00〜18:00（540分）
WITH idx AS (
    SELECT i.id,
           c1.cum_before + CASE WHEN c1.biz = 1 THEN
               (SELECT MIN(v) FROM (VALUES (540.0),
                   ((SELECT MAX(w) FROM (VALUES (0.0), (DATEDIFF(SECOND, CAST(CAST(i.received AS date) AS datetime2), i.received) / 60.0 - 540)) AS t(w)))) AS u(v))
               ELSE 0 END AS b_recv,
           c2.cum_before + CASE WHEN c2.biz = 1 THEN
               (SELECT MIN(v) FROM (VALUES (540.0),
                   ((SELECT MAX(w) FROM (VALUES (0.0), (DATEDIFF(SECOND, CAST(CAST(i.replied AS date) AS datetime2), i.replied) / 60.0 - 540)) AS t(w)))) AS u(v))
               ELSE 0 END AS b_repl
    FROM dbo.inquiries AS i
    JOIN dbo.cal AS c1 ON c1.d = CAST(i.received AS date)
    JOIN dbo.cal AS c2 ON c2.d = CAST(i.replied  AS date)
)
SELECT id, b_repl - b_recv AS biz_min,
       CASE WHEN b_repl - b_recv <= 8 * 60 THEN 1 ELSE 0 END AS within_8h
FROM idx;

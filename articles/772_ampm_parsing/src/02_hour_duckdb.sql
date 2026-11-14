-- 「hh:mm AM/PM」の文字を時に直し、時間帯ごとに数える（DuckDB）
SELECT
    hour(strptime(recv_time, '%I:%M %p'))                    AS hour_ok,     -- 正しい読み（12:xx AM は0時）
    CAST(split_part(recv_time, ':', 1) AS INTEGER)
      + CASE WHEN recv_time LIKE '%PM' THEN 12 ELSE 0 END    AS hour_naive,  -- PM に12を足すだけ
    CAST(split_part(recv_time, ':', 1) AS INTEGER)           AS hour_no_ampm,-- AM/PM を見ない
    COUNT(*) AS n
FROM logs
GROUP BY ALL
ORDER BY hour_ok, hour_naive;

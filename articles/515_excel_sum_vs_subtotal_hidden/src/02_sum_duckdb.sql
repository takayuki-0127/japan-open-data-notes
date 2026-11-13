-- 明細の表（フィルタで隠れた・手で隠した、の印つき）から、3つの合計を出す（DuckDB で実行）
SELECT SUM(amount)                                                         AS sum_all,      -- SUM と同じ
       SUM(amount) FILTER (WHERE NOT filtered_out)                         AS subtotal_9,   -- SUBTOTAL(9) と同じ
       SUM(amount) FILTER (WHERE NOT filtered_out AND NOT manual_hidden)   AS subtotal_109  -- SUBTOTAL(109) と同じ
FROM detail;

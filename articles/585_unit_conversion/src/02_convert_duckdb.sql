-- 入数マスタで「個」に換算して、品目別に足す（DuckDB）
-- unit_master：item・unit（個／箱／ケース）・pcs_per_unit
-- マスタに行がない明細は LEFT JOIN で残し、件数を数える（INNER JOIN だと黙って消える）
SELECT
  s.item,
  SUM(s.qty)                                          AS qty_raw,          -- 換算せずに足した数
  SUM(s.qty * m.pcs_per_unit)                         AS pcs_converted,    -- 換算できた分の個数
  COUNT(*) FILTER (WHERE m.pcs_per_unit IS NULL)      AS unmatched_lines   -- 換算できなかった明細
FROM shipments s
LEFT JOIN unit_master m
  ON m.item = s.item AND m.unit = s.unit
GROUP BY s.item
ORDER BY s.item;

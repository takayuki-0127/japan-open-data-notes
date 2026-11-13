-- 入数マスタで「個」に換算して、品目別に足す（T-SQL、未検証）
SELECT
  s.item,
  SUM(s.qty)                                              AS qty_raw,
  SUM(s.qty * m.pcs_per_unit)                             AS pcs_converted,
  SUM(CASE WHEN m.pcs_per_unit IS NULL THEN 1 ELSE 0 END) AS unmatched_lines
FROM dbo.shipments AS s
LEFT JOIN dbo.unit_master AS m
  ON m.item = s.item AND m.unit = s.unit
GROUP BY s.item
ORDER BY s.item;

-- 入数が変わる品目は、有効期間つきの表（box_size_history）を出荷日で結合する
-- JOIN dbo.box_size_history AS h
--   ON h.item = s.item AND s.shipped_on BETWEEN h.valid_from AND h.valid_to

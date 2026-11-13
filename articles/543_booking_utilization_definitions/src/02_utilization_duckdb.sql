-- 曜日ごとの稼働率を4通りで出す（DuckDB 版。slots(slot_id, day, slot_no)、reservations(res_id, slot_id, booked, status)）
WITH per_slot AS (
  SELECT s.slot_id, s.day,
         COUNT(r.res_id)                                                        AS n_res,
         MAX(CASE WHEN r.status IN ('来店', '無断キャンセル') THEN 1 ELSE 0 END) AS kept,
         MAX(CASE WHEN r.status = '来店' THEN 1 ELSE 0 END)                       AS came
  FROM slots AS s LEFT JOIN reservations AS r ON r.slot_id = s.slot_id
  GROUP BY s.slot_id, s.day)
SELECT ['月', '火', '水', '木', '金', '土', '日'][isodow(day)]          AS wd,
       COUNT(*)                                                      AS slots,
       100.0 * SUM(n_res) / COUNT(*)                                 AS D1,
       100.0 * SUM(CASE WHEN n_res > 0 THEN 1 ELSE 0 END) / COUNT(*) AS D2,
       100.0 * SUM(kept) / COUNT(*)                                  AS D3,
       100.0 * SUM(came) / COUNT(*)                                  AS D4
FROM per_slot
GROUP BY 1;

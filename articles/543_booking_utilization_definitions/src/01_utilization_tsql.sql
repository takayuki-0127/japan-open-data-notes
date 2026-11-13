-- 曜日ごとの稼働率を4通りで出す（T-SQL 版、SQL Server では未検証）
-- dbo.slots(slot_id, day, slot_no)、dbo.reservations(res_id, slot_id, booked, status)
-- 曜日の名前は SET LANGUAGE と DATEFIRST の設定で変わるので、DATEDIFF で月曜=0 にそろえる
WITH per_slot AS (
  SELECT s.slot_id, s.day,
         COUNT(r.res_id)                                                          AS n_res,
         MAX(CASE WHEN r.status IN (N'来店', N'無断キャンセル') THEN 1 ELSE 0 END) AS kept,
         MAX(CASE WHEN r.status = N'来店' THEN 1 ELSE 0 END)                        AS came
  FROM dbo.slots AS s LEFT JOIN dbo.reservations AS r ON r.slot_id = s.slot_id
  GROUP BY s.slot_id, s.day)
SELECT DATEDIFF(day, '19000101', day) % 7                                        AS wd_mon0,
       COUNT(*)                                                                  AS slots,
       100.0 * SUM(n_res) / COUNT(*)                                             AS D1,
       100.0 * SUM(CASE WHEN n_res > 0 THEN 1 ELSE 0 END) / COUNT(*)             AS D2,
       100.0 * SUM(kept) / COUNT(*)                                              AS D3,
       100.0 * SUM(came) / COUNT(*)                                              AS D4
FROM per_slot
GROUP BY DATEDIFF(day, '19000101', day) % 7
ORDER BY wd_mon0;

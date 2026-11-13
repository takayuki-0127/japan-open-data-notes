-- T-SQL 版（SQL Server では動かしていない：未検証）
-- ①イベントごとに10%を残す ②利用者IDのハッシュで10%の人を選ぶ。区分ごとに10倍して戻す
SELECT e.cat,
       COUNT(*) * 10 AS events_x10_by_event
FROM dbo.events AS e
WHERE ABS(CHECKSUM(NEWID())) % 10 = 0
GROUP BY e.cat;

SELECT e.cat,
       COUNT(*) * 10                 AS events_x10_by_user,
       COUNT(DISTINCT e.user_id) * 10 AS users_x10_by_user
FROM dbo.events AS e
WHERE ABS(CHECKSUM(e.user_id)) % 10 = 0
GROUP BY e.cat;

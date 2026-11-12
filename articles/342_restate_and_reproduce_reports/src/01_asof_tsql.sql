-- 342 「いつ時点で見たか」で過去のレポートを作り直す（T-SQL 版。SQL Server 本体では動かしていません＝未検証）
-- C：tx_hist(id INT, ym CHAR(7), tx_date DATE, kind NVARCHAR(4), amt DECIMAL(18,0), rec_from DATETIME2, rec_to DATETIME2 NULL)
--    登録・訂正・取消のたびに、前の行の rec_to を埋めて、新しい行を足す（行は消さない・書き換えない）
DECLARE @ym CHAR(7) = '2025-06', @t DATETIME2 = '2025-07-07T23:00:00';
SELECT SUM(amt) AS reported
FROM tx_hist
WHERE ym = @ym AND kind <> N'取消'
  AND rec_from <= @t AND (rec_to > @t OR rec_to IS NULL);

-- B：今の表 tx_cur と、更新の履歴 tx_update_log(id, changed_at, old, new) から巻き戻す
--    登録した時刻と、取り消した行は残っていないので、遅れて登録された行と取消は戻せない
WITH firstafter AS (
  SELECT id, old, ROW_NUMBER() OVER (PARTITION BY id ORDER BY changed_at) AS rn
  FROM tx_update_log WHERE changed_at > @t)
SELECT SUM(COALESCE(f.old, c.amt)) AS rebuilt
FROM tx_cur AS c LEFT JOIN firstafter AS f ON f.id = c.id AND f.rn = 1
WHERE c.ym = @ym;

-- SQL Server には、行の有効期間を自動で持つ「システムバージョン管理テーブル」があり、
--   SELECT ... FROM tx FOR SYSTEM_TIME AS OF @t WHERE ym = @ym;
-- の形で同じことができる（これも未検証）

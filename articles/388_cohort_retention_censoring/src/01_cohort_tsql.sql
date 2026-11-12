-- 388 登録月×経過月の継続の表（T-SQL。SQL Server 本体では動かしていません＝未検証）
-- members(会員ID, 登録月, 登録日, 退会日)：退会日は、まだ退会していなければ NULL
DECLARE @cut DATE = '2025-12-31';            -- 観測の終わり（データを取り出した日）
WITH k AS (SELECT TOP (23) ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) AS k FROM sys.all_objects),
m AS (
  SELECT m.登録月, k.k,
         CASE WHEN DATEADD(DAY, 30 * k.k, m.登録日) <= @cut THEN 1 ELSE 0 END AS seen,
         CASE WHEN DATEADD(DAY, 30 * k.k, m.登録日) <= @cut
               AND (m.退会日 IS NULL OR m.退会日 > DATEADD(DAY, 30 * k.k, m.登録日)) THEN 1 ELSE 0 END AS alive
  FROM members AS m CROSS JOIN k
)
SELECT 登録月, k,
       COUNT(*)   AS 人数,
       SUM(seen)  AS 観測できた人数,
       SUM(alive) AS 続いていた人数,
       -- 観測できた人が1人もいない所は NULL（空欄）にする。0 にしない
       CAST(100.0 * SUM(alive) / NULLIF(SUM(seen), 0) AS DECIMAL(5,1)) AS 継続率
FROM m
GROUP BY 登録月, k
ORDER BY 登録月, k;

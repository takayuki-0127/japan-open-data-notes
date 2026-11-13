-- T-SQL：未検証
-- 注意：SQL Server の既定の照合順序は大文字小文字を区別しないことが多く、その場合 COUNT(DISTINCT email) は大文字の違いを同じとみなす
SELECT
  COUNT(*)                                                     AS entries,
  COUNT(DISTINCT email COLLATE Japanese_BIN2)                  AS exact_email,
  COUNT(DISTINCT LOWER(LTRIM(RTRIM(email))))                   AS norm_email
FROM dbo.entries;

-- 1人1口にした抽選の対象（最初の登録を残す）
WITH d AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY LOWER(LTRIM(RTRIM(email))) ORDER BY entry_id) AS rn
  FROM dbo.entries
)
SELECT entry_id, email FROM d WHERE rn = 1;

-- 重複を除いたあとの件数（DuckDB）
SELECT
  COUNT(*)                                        AS entries,
  COUNT(DISTINCT email)                           AS exact_email,
  COUNT(DISTINCT LOWER(TRIM(email)))              AS norm_email
FROM entries;

-- メールをそろえたうえで、1人1口にした抽選の対象（最初の登録を残す）
-- SELECT * FROM (
--   SELECT *, ROW_NUMBER() OVER (PARTITION BY LOWER(TRIM(email)) ORDER BY entry_id) AS rn FROM entries
-- ) WHERE rn = 1;

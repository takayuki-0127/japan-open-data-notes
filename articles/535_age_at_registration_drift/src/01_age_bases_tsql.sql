-- 年代別の構成を「登録時の年齢」と「基準日の年齢」で並べる（T-SQL 版、SQL Server では未検証）
-- dbo.members(member_id, birth_date DATE, registered_on DATE)
-- DATEDIFF(year, ...) は年の境目をまたいだ回数なので、誕生日がまだ来ていなければ1を引く
DECLARE @asof DATE = '2026-03-31';
WITH a AS (
  SELECT member_id,
         DATEDIFF(year, birth_date, registered_on)
           - CASE WHEN MONTH(registered_on) * 100 + DAY(registered_on) < MONTH(birth_date) * 100 + DAY(birth_date) THEN 1 ELSE 0 END AS age_reg,
         DATEDIFF(year, birth_date, @asof)
           - CASE WHEN MONTH(@asof) * 100 + DAY(@asof) < MONTH(birth_date) * 100 + DAY(birth_date) THEN 1 ELSE 0 END AS age_now
  FROM dbo.members),
b AS (
  SELECT CASE WHEN age_reg >= 70 THEN 70 ELSE age_reg / 10 * 10 END AS band_reg,
         CASE WHEN age_now >= 70 THEN 70 ELSE age_now / 10 * 10 END AS band_now
  FROM a)
SELECT x.band,
       100.0 * SUM(CASE WHEN x.kind = 'reg' THEN 1 ELSE 0 END) / COUNT(*) OVER () * 2 AS pct_reg,
       100.0 * SUM(CASE WHEN x.kind = 'now' THEN 1 ELSE 0 END) / COUNT(*) OVER () * 2 AS pct_now
FROM (SELECT band_reg AS band, 'reg' AS kind FROM b UNION ALL SELECT band_now, 'now' FROM b) AS x
GROUP BY x.band
ORDER BY x.band;

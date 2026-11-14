-- T-SQL：未検証
-- 番号の偶数・奇数で分ける（番号の振り方しだいで偏る）
SELECT member_id % 2 AS grp, COUNT(*) AS n, AVG(CAST(spend AS float)) AS mean_spend
FROM dbo.members GROUP BY member_id % 2;
-- ハッシュで分ける（実験ごとに文字を変えると、別の分け方になる）
SELECT ABS(CHECKSUM(HASHBYTES('SHA2_256', CONCAT(member_id, '-exp744')))) % 2 AS grp,
       COUNT(*) AS n, AVG(CAST(spend AS float)) AS mean_spend
FROM dbo.members
GROUP BY ABS(CHECKSUM(HASHBYTES('SHA2_256', CONCAT(member_id, '-exp744')))) % 2;

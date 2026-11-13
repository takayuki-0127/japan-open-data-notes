-- T-SQL 版（SQL Server では動かしていない：未検証）
DECLARE @eval date = '2025-06-30';
WITH last_buy AS (
  SELECT member_id, MAX(bought_on) AS last_on
  FROM dbo.purchases
  WHERE bought_on <= @eval
  GROUP BY member_id
)
SELECT SUM(CASE WHEN DATEDIFF(DAY, last_on, @eval) > 90  THEN 1 ELSE 0 END) AS dormant_90,
       SUM(CASE WHEN DATEDIFF(DAY, last_on, @eval) > 180 THEN 1 ELSE 0 END) AS dormant_180,
       COUNT(*) AS members
FROM last_buy;

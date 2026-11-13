-- T-SQL 版（SQL Server では動かしていない：未検証）
-- 相関は式で計算する（SQL Server には CORR 関数がない）
WITH d AS (
    SELECT [case], old_kg, new_kg, new_kg - old_kg AS diff
    FROM dbo.paired
), s AS (
    SELECT [case],
           COUNT(*) AS n,
           AVG(old_kg) AS mo, AVG(new_kg) AS mn,
           AVG(diff) AS mean_diff, STDEV(diff) AS sd_diff,
           SUM(old_kg * new_kg) AS sxy, SUM(old_kg * old_kg) AS sxx, SUM(new_kg * new_kg) AS syy
    FROM d
    GROUP BY [case]
)
SELECT [case],
       (sxy - n * mo * mn) / SQRT((sxx - n * mo * mo) * (syy - n * mn * mn)) AS r,
       mean_diff,
       sd_diff,
       mean_diff - 1.96 * sd_diff AS loa_low,
       mean_diff + 1.96 * sd_diff AS loa_high
FROM s
ORDER BY [case];

-- T-SQL 版（SQL Server では動かしていない：未検証）
SELECT b.band, COUNT(*) AS n,
       AVG(CASE WHEN p.sales < p.lo OR p.sales > p.hi THEN 1.0 ELSE 0.0 END) AS miss_rate,
       AVG(p.hi - p.lo) AS avg_width
FROM dbo.pred AS p
CROSS APPLY (SELECT CASE WHEN FLOOR((p.area - 1) / 0.9) > 9 THEN 9
                         ELSE CAST(FLOOR((p.area - 1) / 0.9) AS int) END AS band) AS b
GROUP BY b.band
ORDER BY b.band;

-- 04 列（業態）を表から読んで PIVOT を組み立てる動的 SQL（T-SQL）。SQL Server 専用のため未検証
DECLARE @cols NVARCHAR(MAX), @sql NVARCHAR(MAX);
SELECT @cols = STRING_AGG(QUOTENAME(gyotai), N', ') WITHIN GROUP (ORDER BY gyotai)
FROM (SELECT DISTINCT gyotai FROM dbo.sales_monthly) AS g;
SET @sql = N'SELECT yr, ' + @cols + N'
FROM (SELECT YEAR(ym) AS yr, gyotai, sales FROM dbo.sales_monthly WHERE ym < ''2026-01-01'') AS src
PIVOT (SUM(sales) FOR gyotai IN (' + @cols + N')) AS p
ORDER BY yr;';
EXEC sp_executesql @sql;

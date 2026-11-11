-- 03 同じことを T-SQL の PIVOT で。SQL Server 専用の構文のため、この記事の環境では未検証
SELECT yr, [コンビニ], [スーパー], [ドラッグストア], [ホームセンター], [家電大型専門店], [百貨店]
FROM (
    SELECT YEAR(ym) AS yr, gyotai, sales
    FROM dbo.sales_monthly
    WHERE ym < '2026-01-01'
) AS src
PIVOT (SUM(sales) FOR gyotai IN ([コンビニ], [スーパー], [ドラッグストア], [ホームセンター], [家電大型専門店], [百貨店])) AS p
ORDER BY yr;

-- 05 形を変えたあとの照合（T-SQL と DuckDB の両方で動く書き方。DuckDB で検証）
-- (a) 同じキーの行が2つ以上ないか（PIVOT の SUM は重複を黙って足す）
SELECT gyotai, ym, COUNT(*) AS n
FROM dbo.sales_monthly
GROUP BY gyotai, ym
HAVING COUNT(*) > 1;

-- (b) 縦長の合計と、横長に並べた列の合計が同じか（CASE WHEN に無い業態は黙って落ちる）
SELECT SUM(sales) AS total_long,
       SUM(CASE WHEN gyotai IN (N'コンビニ', N'スーパー', N'ドラッグストア',
                                N'ホームセンター', N'家電大型専門店', N'百貨店') THEN sales END) AS total_in_columns
FROM dbo.sales_monthly
WHERE ym < '2026-01-01';

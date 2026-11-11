-- 02 縦長→横長（年×業態）。CASE WHEN で列を作る書き方。T-SQL と DuckDB の両方で同じ文が動く（DuckDB で検証）
SELECT YEAR(ym) AS yr,
       SUM(CASE WHEN gyotai = N'コンビニ'       THEN sales END) AS conveni,
       SUM(CASE WHEN gyotai = N'スーパー'       THEN sales END) AS super,
       SUM(CASE WHEN gyotai = N'ドラッグストア' THEN sales END) AS drug,
       SUM(CASE WHEN gyotai = N'ホームセンター' THEN sales END) AS homecenter,
       SUM(CASE WHEN gyotai = N'家電大型専門店' THEN sales END) AS kaden,
       SUM(CASE WHEN gyotai = N'百貨店'         THEN sales END) AS depart,
       COUNT(*) AS n_rows
FROM dbo.sales_monthly
WHERE ym < '2026-01-01'
GROUP BY YEAR(ym)
ORDER BY yr;

-- 週番号の決め方を変えて、前年同週比を出す（DuckDB 版）
-- daily(d DATE, sales BIGINT)
-- A 年の初めから7日ずつ区切る週（1月1日から1〜7日が第1週。最後の週は1〜2日だけ）
-- B 日曜始まりで、1月1日を含む週を第1週とする週（DATEPART(week) と同じ数え方。最初と最後の週は短い）
-- C ISO 週（月曜始まり。1年は52週か53週、どの週も7日）
WITH w AS (
  SELECT d, sales,
         year(d) AS y,
         (dayofyear(d) - 1) // 7 + 1 AS wk_a,
         CAST(strftime(d, '%U') AS INTEGER) + CASE WHEN strftime(make_date(year(d), 1, 1), '%w') = '0' THEN 0 ELSE 1 END AS wk_b,
         isoyear(d) AS iy, weekofyear(d) AS wk_c
  FROM daily)
SELECT 'A' AS method, y AS yr, wk_a AS wk, COUNT(*) AS days, SUM(sales) AS sales FROM w GROUP BY y, wk_a
UNION ALL
SELECT 'B', y, wk_b, COUNT(*), SUM(sales) FROM w GROUP BY y, wk_b
UNION ALL
SELECT 'C', iy, wk_c, COUNT(*), SUM(sales) FROM w GROUP BY iy, wk_c
ORDER BY method, yr, wk;
-- 前年同週比（同じ週番号どうしを結ぶ。前年にない週番号は NULL）
-- weekly(method, yr, wk, days, sales) は上の結果
SELECT t.method, t.yr, t.wk, t.days, p.days AS prev_days,
       ROUND((t.sales * 1.0 / p.sales - 1) * 100, 1) AS yoy_pct
FROM weekly t LEFT JOIN weekly p ON p.method = t.method AND p.yr = t.yr - 1 AND p.wk = t.wk
WHERE t.yr IN (2025, 2026)
ORDER BY t.method, t.yr, t.wk;

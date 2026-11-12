-- 3つの「週」で週次の売上を出す（DuckDB で実行した版）
SELECT 'ISO' AS def, isoyear(d) AS y, weekofyear(d) AS w, 0 AS m,
       COUNT(*) AS days, SUM(amount) AS sales, MIN(d) AS d0
FROM sales GROUP BY ALL
UNION ALL
-- 日曜始まり・1月1日の週が第1週（SQL Server の DATEPART(week) と同じ数え方を式で書いた）
SELECT 'SUN', year(d),
       CAST(floor((dayofyear(d) + dayofweek(make_date(year(d), 1, 1)) - 1) / 7) AS INTEGER) + 1, 0,
       COUNT(*), SUM(amount), MIN(d)
FROM sales GROUP BY ALL
UNION ALL
-- 月で切る週：月曜始まりの週を、月の境目でも切る
SELECT 'MONTH', year(d),
       CAST(floor((day(d) + isodow(make_date(year(d), month(d), 1)) - 2) / 7) AS INTEGER) + 1, month(d),
       COUNT(*), SUM(amount), MIN(d)
FROM sales GROUP BY ALL
ORDER BY 1, d0;

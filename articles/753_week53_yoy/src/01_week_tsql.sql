-- T-SQL：未検証（SQL Server では動かしていない）
-- B DATEPART(week)：1月1日を含む週が第1週（週の始まりは SET DATEFIRST による。既定は日曜）
-- C DATEPART(iso_week)：ISO 週。ISO の年は DATEPART(year) ではなく、その週の木曜日の年で決まる
WITH w AS (
  SELECT d, sales,
         YEAR(d) AS y,
         DATEPART(week, d) AS wk_b,
         DATEPART(iso_week, d) AS wk_c
  FROM dbo.daily)
SELECT y AS yr, wk_b AS wk, COUNT(*) AS days, SUM(sales) AS sales
FROM w GROUP BY y, wk_b ORDER BY y, wk_b;
-- 364日前と比べる（曜日がそろう）
SELECT t.d, t.sales, p.sales AS sales_364,
       CAST(t.sales AS float) / NULLIF(p.sales, 0) - 1 AS yoy
FROM dbo.daily t LEFT JOIN dbo.daily p ON p.d = DATEADD(day, -364, t.d);

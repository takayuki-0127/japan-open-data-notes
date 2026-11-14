-- T-SQL：未検証
-- 店ごとの前年比・寄与度・寄与率。@scene に場面（'A' か 'B'）を入れる。sales が整数型なら 1.0 を掛けて小数にする
DECLARE @scene char(1) = 'A';
WITH w AS (
  SELECT store,
         SUM(CASE WHEN [year] = 2024 THEN sales * 1.0 END) AS prev,
         SUM(CASE WHEN [year] = 2025 THEN sales * 1.0 END) AS cur
  FROM dbo.store_sales WHERE scene = @scene
  GROUP BY store
)
SELECT store,
       100.0 * (cur / prev - 1)                                          AS yoy,
       100.0 * (cur - prev) / SUM(prev) OVER ()                          AS contrib_pt,
       100.0 * (cur - prev) / NULLIF(SUM(cur) OVER () - SUM(prev) OVER (), 0) AS contrib_share
FROM w
ORDER BY contrib_pt DESC;

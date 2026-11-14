-- 店ごとの前年比・寄与度・寄与率（DuckDB）。? に場面（'A' か 'B'）を入れる
WITH w AS (
  SELECT store,
         SUM(CASE WHEN year = 2024 THEN sales END) AS prev,
         SUM(CASE WHEN year = 2025 THEN sales END) AS cur
  FROM store_sales WHERE scene = ?
  GROUP BY store
)
SELECT store,
       100.0 * (cur / prev - 1)                                    AS yoy,            -- 前年比
       100.0 * (cur - prev) / SUM(prev) OVER ()                    AS contrib_pt,     -- 寄与度（ポイント）
       100.0 * (cur - prev) / (SUM(cur) OVER () - SUM(prev) OVER ()) AS contrib_share -- 寄与率（%）
FROM w
ORDER BY contrib_pt DESC;

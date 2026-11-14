-- 申込み率の変化を、ポイントの差・%の変化・件数の差の3つで並べる（DuckDB 版）
-- stores(store_id, visits1, apps1, visits2, apps2)
WITH r AS (
  SELECT store_id,
         apps1 * 100.0 / visits1 AS rate1, apps2 * 100.0 / visits2 AS rate2,
         apps2 - apps1 AS diff_apps
  FROM stores)
SELECT store_id, rate1, rate2,
       rate2 - rate1                         AS diff_pt,
       (rate2 / rate1 - 1) * 100             AS change_pct,
       diff_apps,
       RANK() OVER (ORDER BY rate2 - rate1 DESC)        AS rank_pt,
       RANK() OVER (ORDER BY rate2 / rate1 DESC)        AS rank_pct,
       RANK() OVER (ORDER BY diff_apps DESC)            AS rank_apps
FROM r
ORDER BY store_id;

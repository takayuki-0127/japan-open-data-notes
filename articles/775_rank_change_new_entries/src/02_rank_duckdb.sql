-- 2期の順位を3通りで比べる（DuckDB）
WITH r AS (   -- その期にいた店の中での順位
    SELECT period, store_id, sales,
           RANK() OVER (PARTITION BY period ORDER BY sales DESC) AS rk
    FROM sales
),
common_rk AS (     -- 両方の期にいた店だけで順位を付け直す（順位を詰める）
    SELECT period, store_id,
           RANK() OVER (PARTITION BY period ORDER BY sales DESC) AS rk_common
    FROM sales
    WHERE store_id IN (SELECT store_id FROM sales WHERE period = 1)
      AND store_id IN (SELECT store_id FROM sales WHERE period = 2)
),
n1 AS (SELECT COUNT(*) AS n FROM sales WHERE period = 1)
SELECT c.store_id,
       p.rk                                  AS rank_prev,          -- 前回の順位（いなければ NULL）
       c.rk                                  AS rank_now,
       COALESCE(p.rk, (SELECT n FROM n1) + 1) AS rank_prev_bottom,  -- いなかった店は最下位の次とする
       bp.rk_common                          AS rank_prev_common,
       bc.rk_common                          AS rank_now_common
FROM r AS c
LEFT JOIN r    AS p  ON p.store_id = c.store_id AND p.period = 1
LEFT JOIN common_rk AS bp ON bp.store_id = c.store_id AND bp.period = 1
LEFT JOIN common_rk AS bc ON bc.store_id = c.store_id AND bc.period = 2
WHERE c.period = 2
ORDER BY c.store_id;

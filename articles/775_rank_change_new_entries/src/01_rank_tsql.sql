-- T-SQL：未検証
WITH r AS (
    SELECT period, store_id, sales, RANK() OVER (PARTITION BY period ORDER BY sales DESC) AS rk
    FROM dbo.sales
),
common_rk AS (
    SELECT period, store_id, RANK() OVER (PARTITION BY period ORDER BY sales DESC) AS rk_common
    FROM dbo.sales
    WHERE store_id IN (SELECT store_id FROM dbo.sales WHERE period = 1)
      AND store_id IN (SELECT store_id FROM dbo.sales WHERE period = 2)
)
SELECT c.store_id, p.rk AS rank_prev, c.rk AS rank_now,
       COALESCE(p.rk, (SELECT COUNT(*) FROM dbo.sales WHERE period = 1) + 1) AS rank_prev_bottom,
       bp.rk_common AS rank_prev_common, bc.rk_common AS rank_now_common
FROM r AS c
LEFT JOIN r    AS p  ON p.store_id = c.store_id AND p.period = 1
LEFT JOIN common_rk AS bp ON bp.store_id = c.store_id AND bp.period = 1
LEFT JOIN common_rk AS bc ON bc.store_id = c.store_id AND bc.period = 2
WHERE c.period = 2
ORDER BY c.store_id;

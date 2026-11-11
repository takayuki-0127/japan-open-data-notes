-- F232：階層・予測の先（3区分）・方法ごとの MAPE と、ベースに対する改善率
WITH bucketed AS (
    SELECT cond, method, level, ape,
           CASE WHEN horizon <= 3 THEN '1-3' WHEN horizon <= 6 THEN '4-6' ELSE '7-12' END AS hbucket
    FROM ape_long
),
mape AS (
    SELECT cond, method, level, hbucket, AVG(ape) AS mape, COUNT(*) AS n
    FROM bucketed
    GROUP BY cond, method, level, hbucket
)
SELECT m.cond, m.level, m.hbucket, m.method,
       ROUND(m.mape, 3) AS mape,
       ROUND((m.mape / b.mape - 1.0) * 100.0, 2) AS vs_base_pct,
       RANK() OVER (PARTITION BY m.cond, m.level, m.hbucket ORDER BY m.mape) AS rank_in_level
FROM mape AS m
JOIN mape AS b
  ON b.cond = m.cond AND b.level = m.level AND b.hbucket = m.hbucket
 AND b.method = N'ベース（そろえない）'
ORDER BY m.cond, m.level, m.hbucket, m.mape;

-- F232：親の予測と、子の予測の合計がそろっているか（つじつまの検算）
-- そろえた予測（MinT など）は、どの親子でもずれが 0 になるはず
WITH child_sum AS (
    SELECT method, parent, ym, SUM(forecast) AS children_total, COUNT(*) AS n_children
    FROM forecast_long
    WHERE parent IS NOT NULL AND parent <> ''
    GROUP BY method, parent, ym
)
SELECT c.method,
       p.level                                   AS parent_level,
       COUNT(*)                                  AS n_checks,
       MAX(ABS(c.children_total - p.forecast) / p.forecast * 100.0) AS max_gap_pct,
       AVG(ABS(c.children_total - p.forecast) / p.forecast * 100.0) AS mean_gap_pct
FROM child_sum AS c
JOIN forecast_long AS p
  ON p.method = c.method AND p.node = c.parent AND p.ym = c.ym
GROUP BY c.method, p.level
ORDER BY c.method, p.level;

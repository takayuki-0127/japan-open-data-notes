-- 損害1件ごとに、比例てん補と実損てん補の支払を出して合計する（DuckDB）
-- 入力 loss_events(value, damage_ratio, loss)。付保割合 k は 0.6
WITH p AS (
  SELECT loss,
         0.6 * value                     AS sum_insured,
         loss * LEAST(1.0, 0.6)          AS paid_prop,    -- 比例てん補
         LEAST(loss, 0.6 * value)        AS paid_first    -- 実損てん補（保険金額まで）
  FROM loss_events
)
SELECT COUNT(*) AS n, SUM(loss) AS loss, SUM(paid_prop) AS paid_prop, SUM(paid_first) AS paid_first,
       SUM(paid_prop) / SUM(loss) AS share_prop, SUM(paid_first) / SUM(loss) AS share_first
FROM p;

-- 比例てん補と実損てん補の支払（T-SQL 版。SQL Server では動かしていない：未検証）
-- 入力 dbo.loss_events(value FLOAT, damage_ratio FLOAT, loss FLOAT)。付保割合 k は 0.6
WITH p AS (
  SELECT loss,
         0.6 * value AS sum_insured,
         loss * 0.6 AS paid_prop,
         CASE WHEN loss < 0.6 * value THEN loss ELSE 0.6 * value END AS paid_first
  FROM dbo.loss_events
)
SELECT COUNT(*) AS n, SUM(loss) AS loss, SUM(paid_prop) AS paid_prop, SUM(paid_first) AS paid_first,
       SUM(paid_prop) / SUM(loss) AS share_prop, SUM(paid_first) / SUM(loss) AS share_first
FROM p;

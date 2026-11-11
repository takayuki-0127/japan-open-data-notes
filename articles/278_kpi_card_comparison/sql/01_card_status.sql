-- KPI カードの「良い／悪い」を、3つの比べ方で同時に判定する（T-SQL）
-- direction = 1：大きいほど良い、-1：小さいほど良い
WITH base AS (
    SELECT kpi, ym, value, target, direction,
           LAG(value, 1)  OVER (PARTITION BY kpi ORDER BY ym) AS prev_month,
           LAG(value, 12) OVER (PARTITION BY kpi ORDER BY ym) AS prev_year
    FROM dbo.kpi_monthly
)
SELECT kpi, ym, value,
       CASE WHEN prev_month IS NULL THEN NULL
            WHEN (value - prev_month) * direction > 0 THEN 1 ELSE -1 END AS good_mom,
       CASE WHEN prev_year IS NULL THEN NULL
            WHEN (value - prev_year) * direction > 0 THEN 1 ELSE -1 END AS good_yoy,
       CASE WHEN (value - target) * direction >= 0 THEN 1 ELSE -1 END AS good_target
FROM base;

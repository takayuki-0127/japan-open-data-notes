-- 週の途中の比べ方（DuckDB 版）。daily(store, d DATE, sales)。週は月曜始まり。$asof の日の終わりに見る
WITH p AS (
  SELECT date_trunc('week', $asof::DATE) AS wk, $asof::DATE AS asof
)
SELECT
  SUM(sales) FILTER (WHERE d >= p.wk AND d <= p.asof)                                   AS this_week_to_date,
  SUM(sales) FILTER (WHERE d >= p.wk - INTERVAL 7 DAY AND d < p.wk)                     AS last_week_total,
  SUM(sales) FILTER (WHERE d >= p.wk - INTERVAL 7 DAY AND d <= p.asof - INTERVAL 7 DAY) AS last_week_to_same_day
FROM daily, p
WHERE store = $store;

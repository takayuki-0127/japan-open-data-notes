-- SQL Server 互換の書き方（DuckDB で動作確認）。テーブル drugstore_monthly(ym, 業態, 地域, 品目, 指標, 値)
-- 1) 8月の前年同月比（全国・地域）
WITH s AS (
  SELECT 地域, 品目, ym, 値 FROM drugstore_monthly
  WHERE 指標 = '販売額' AND ym IN ('2025-08','2026-08')
    AND ((地域 = '全国' AND 品目 = '商品販売額') OR (地域 <> '全国' AND 品目 = '販売額'))
)
SELECT 地域,
       100.0 * SUM(CASE WHEN ym = '2026-08' THEN 値 END) / SUM(CASE WHEN ym = '2025-08' THEN 値 END) - 100 AS yoy
FROM s GROUP BY 地域 ORDER BY 地域;
-- 2) 品目別の寄与（全国、ポイント）
WITH it AS (
  SELECT 品目,
         SUM(CASE WHEN ym = '2026-08' THEN 値 END) AS a,
         SUM(CASE WHEN ym = '2025-08' THEN 値 END) AS b
  FROM drugstore_monthly
  WHERE 地域 = '全国' AND 指標 = '販売額' AND 品目 <> '商品販売額' AND ym IN ('2025-08','2026-08')
  GROUP BY 品目
)
SELECT 品目, 100.0 * (a - b) / SUM(b) OVER () AS contrib_pt FROM it ORDER BY contrib_pt;

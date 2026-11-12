-- 441 基準の年が変わった指数を「年平均でつなぐ」係数（T-SQL 版。SQL Server 本体では未検証。同じ考え方の SQL を DuckDB で実行して確かめた）
-- cpi(base INT, series NVARCHAR(40), ym CHAR(7), value DECIMAL(9,1))  … base はその数字の基準年、ym は 'YYYY-MM'
WITH nat AS (            -- その基準が現役だった月（基準年の1月以降）だけ
  SELECT base, series, ym, value FROM cpi WHERE ym >= CAST(base AS CHAR(4)) + '-01'
),
f AS (                   -- 新しい基準年の12か月で、旧基準の平均 ÷ 新基準の平均
  SELECT o.base AS old_base, n.base AS new_base, o.series,
         AVG(CAST(o.value AS FLOAT)) / AVG(CAST(n.value AS FLOAT)) AS factor
  FROM nat o
  JOIN nat n ON n.series = o.series AND n.ym = o.ym AND n.base = o.base + 5
  WHERE LEFT(o.ym, 4) = CAST(n.base AS CHAR(4))
  GROUP BY o.base, n.base, o.series
)
SELECT old_base, new_base, series, factor FROM f ORDER BY old_base, series;
-- 1か月でつなぐ場合は、WHERE を  o.ym = CAST(n.base AS CHAR(4)) + '-01'  のように1か月に絞る

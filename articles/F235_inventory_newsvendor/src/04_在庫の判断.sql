-- F235 在庫の判断を SQL で（SQL Server 互換の書き方）
-- 前提：data/forecasts_h1to3.csv を表 forecast に取り込む
--   列：実験, 業態, 起点, 対象月('YYYY-MM'), h, モデル, 実績, 予測, 下80, 上80, 比, コロナ期
-- SQL Server での取り込み例：
--   CREATE TABLE forecast (実験 NVARCHAR(10), 業態 NVARCHAR(20), 起点 CHAR(7), 対象月 CHAR(7), h INT, モデル NVARCHAR(20),
--                          実績 FLOAT, 予測 FLOAT, 下80 FLOAT NULL, 上80 FLOAT NULL, 比 FLOAT, コロナ期 NVARCHAR(5));
--   BULK INSERT forecast FROM 'forecasts_h1to3.csv' WITH (FORMAT='CSV', FIRSTROW=2, CODEPAGE='65001');
-- 損の比 cu/co = 9（足りない1単位の損が、余る1単位の損の9倍。例として置いた値）→ 目標のサービス率 0.9

-- 1) 2017〜2019年の外れ（実績÷予測）の90%点を、業態×モデルごとに求める（＝発注の倍率）
WITH cal AS (
  SELECT DISTINCT モデル, 業態,
         PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY 比) OVER (PARTITION BY モデル, 業態) AS 倍率,
         COUNT(*) OVER (PARTITION BY モデル, 業態) AS n_cal
  FROM forecast
  WHERE h = 1 AND コロナ期 = 'False' AND 対象月 <= '2019-12'
),
-- 2) 2022年以降の月に、その倍率で発注した場合の不足・余り（需要100あたり）
test AS (
  SELECT f.モデル, f.業態, f.対象月, f.実績, f.予測 * c.倍率 AS 発注
  FROM forecast AS f
  JOIN cal AS c ON c.モデル = f.モデル AND c.業態 = f.業態
  WHERE f.h = 1 AND f.コロナ期 = 'False' AND f.対象月 >= '2022-01'
)
SELECT t.モデル, t.業態, MAX(c.倍率) AS 倍率q90, MAX(c.n_cal) AS n_cal, COUNT(*) AS n_test,
       AVG(9.0 * CASE WHEN t.実績 > t.発注 THEN (t.実績 - t.発注) / t.実績 * 100 ELSE 0 END
               + CASE WHEN t.発注 > t.実績 THEN (t.発注 - t.実績) / t.実績 * 100 ELSE 0 END) AS 損,
       AVG(CASE WHEN t.実績 <= t.発注 THEN 1.0 ELSE 0.0 END) AS サービス率
FROM test AS t
JOIN cal AS c ON c.モデル = t.モデル AND c.業態 = t.業態
GROUP BY t.モデル, t.業態
ORDER BY t.モデル, t.業態;

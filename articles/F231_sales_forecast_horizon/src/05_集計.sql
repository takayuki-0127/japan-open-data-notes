-- F231 予測の地平ごとの外れ（MAPE）を SQL で集計する（SQL Server 互換の書き方。SQLite でも同じ結果になることを確かめた）
-- 前提：results/forecasts_main.csv.gz を表 forecast に取り込む
--   列：実験, 業態, 起点, 対象月('YYYY-MM'), h, モデル, 実績, 予測, 下80, 上80
-- SQL Server での取り込み例：
--   CREATE TABLE forecast (実験 NVARCHAR(40), 業態 NVARCHAR(20), 起点 CHAR(7), 対象月 CHAR(7), h INT,
--                          モデル NVARCHAR(20), 実績 FLOAT, 予測 FLOAT, 下80 FLOAT NULL, 上80 FLOAT NULL);
--   BULK INSERT forecast FROM 'forecasts_main.csv' WITH (FORMAT='CSV', FIRSTROW=2, CODEPAGE='65001');

-- 1) 予測の地平×モデルの MAPE（コロナ期 2020-03〜2021-12 の月は採点しない）
SELECT モデル, h,
       AVG(ABS(予測 / 実績 - 1.0)) * 100 AS mape_pct,
       COUNT(*) AS n
FROM forecast
WHERE 対象月 NOT BETWEEN '2020-03' AND '2021-12'
GROUP BY モデル, h
ORDER BY h, モデル;

-- 2) 季節ナイーブ（去年の同じ月をそのまま使う）と比べた改善の割合（スキル）
WITH m AS (
  SELECT モデル, h, AVG(ABS(予測 / 実績 - 1.0)) * 100 AS mape_pct
  FROM forecast
  WHERE 対象月 NOT BETWEEN '2020-03' AND '2021-12'
  GROUP BY モデル, h
)
SELECT a.モデル, a.h, a.mape_pct, b.mape_pct AS snaive_pct,
       1.0 - a.mape_pct / b.mape_pct AS skill
FROM m AS a
JOIN m AS b ON b.h = a.h AND b.モデル = N'季節ナイーブ'
WHERE a.モデル <> N'季節ナイーブ'
ORDER BY a.h, a.モデル;

-- 3) 検算：1行ずつの外れの合計を、業態ごとに数えて全体と一致するか
SELECT 業態, COUNT(*) AS n, SUM(ABS(予測 / 実績 - 1.0)) AS sum_ape
FROM forecast
WHERE 対象月 NOT BETWEEN '2020-03' AND '2021-12'
GROUP BY 業態
ORDER BY 業態;

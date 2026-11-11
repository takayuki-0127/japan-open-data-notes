-- F259 SQL 検算（SQL Server で動く書き方。DuckDB で実行して Python と照合）
-- 表：demand(業態, 月番号, 需要)  forecasts(業態, モデル, 起点番号, h, 予測)  sim_log(業態, モデル, L, 決め方, 月, 需要, 月末在庫, 売り逃し, 発注量)
-- 月番号 = 年*12 + 月 - 1。コロナ期は 2020-03〜2021-12（月番号 24242〜24263）

-- (1) 在庫の推移の記録から、月あたりの費用を集計する（h=1、p=9、売り逃し）
SELECT "業態", "モデル", "L", "決め方",
       AVG(CASE WHEN "月末在庫" > 0 THEN "月末在庫" ELSE 0 END) + 9 * AVG("売り逃し") AS "費用"
FROM sim_log
GROUP BY "業態", "モデル", "L", "決め方";

-- (2) L+R か月の合計の外れ（実績の合計 − 予測の合計）の RMSE を、1か月先の RMSE で割った倍率
WITH win AS (
  SELECT f."業態", f."モデル", f."起点番号", w.H,
         SUM(d."需要" - f."予測") AS "合計の外れ",
         MAX(CASE WHEN d."月番号" BETWEEN 24242 AND 24263 THEN 1 ELSE 0 END) AS covid
  FROM forecasts AS f
  JOIN (SELECT 1 AS H UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4 UNION ALL SELECT 5 UNION ALL SELECT 6) AS w ON f.h <= w.H
  JOIN demand AS d ON d."業態" = f."業態" AND d."月番号" = f."起点番号" + f.h
  GROUP BY f."業態", f."モデル", f."起点番号", w.H
), r AS (
  SELECT "業態", "モデル", H, SQRT(AVG("合計の外れ" * "合計の外れ")) AS rmse
  FROM win WHERE covid = 0 GROUP BY "業態", "モデル", H
)
SELECT a."業態", a."モデル", a.H, a.rmse / b.rmse AS "RMSE倍"
FROM r AS a JOIN r AS b ON a."業態" = b."業態" AND a."モデル" = b."モデル" AND b.H = 1;

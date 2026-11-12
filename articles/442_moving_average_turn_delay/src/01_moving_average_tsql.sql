-- 442 後ろ7日・後ろ28日の移動平均と「7日前より低い」の印（T-SQL 版。SQL Server 本体では未検証。同じ SQL を DuckDB で実行して確かめた）
-- daily(series_id INT, d INT, value FLOAT)   … d は1日ごとの通し番号（日付でも同じ）
WITH ma AS (
  SELECT series_id, d, value,
         AVG(value) OVER (PARTITION BY series_id ORDER BY d ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)  AS ma7,
         AVG(value) OVER (PARTITION BY series_id ORDER BY d ROWS BETWEEN 27 PRECEDING AND CURRENT ROW) AS ma28,
         COUNT(*)   OVER (PARTITION BY series_id ORDER BY d ROWS BETWEEN 27 PRECEDING AND CURRENT ROW) AS n28
  FROM daily
)
SELECT series_id, d, value, ma7, ma28,
       CASE WHEN ma7  < LAG(ma7, 7)  OVER (PARTITION BY series_id ORDER BY d) THEN 1 ELSE 0 END AS down7,
       CASE WHEN n28 = 28 AND ma28 < LAG(ma28, 7) OVER (PARTITION BY series_id ORDER BY d) THEN 1 ELSE 0 END AS down28
FROM ma
ORDER BY series_id, d;

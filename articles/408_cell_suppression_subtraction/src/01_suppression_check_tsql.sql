-- 408 公表する前の確かめ：隠したセルが1つだけの行・列がないか（あると、合計からの引き算で分かる）
-- T-SQL の書き方。SQL Server 本体では動かしていません（未検証）。同じ数え方を DuckDB で実行しています（src/a408_suppression.py）
-- cells(地域, 年齢, 件数)。1以上10未満のセルを隠す

WITH h AS (
  SELECT 地域, 年齢, 件数,
         CASE WHEN 件数 >= 1 AND 件数 < 10 THEN 1 ELSE 0 END AS 隠す
  FROM dbo.cells
)
SELECT N'行' AS 向き, 地域 AS 名前, SUM(隠す) AS 隠したセル
FROM h GROUP BY 地域 HAVING SUM(隠す) = 1
UNION ALL
SELECT N'列', 年齢, SUM(隠す)
FROM h GROUP BY 年齢 HAVING SUM(隠す) = 1;
-- 1行でも返れば、そのセルは「合計 − 出ているセルの合計」で分かる。
-- その行・列で、出ているセルのうちいちばん小さいものを追加で隠し、もう一度この確かめを流す（0行になるまで）

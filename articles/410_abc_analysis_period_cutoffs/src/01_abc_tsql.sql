-- 410 ABC 分析：売上の大きい順に並べ、累計の割合で A・B・C を付ける
-- T-SQL の書き方。SQL Server 本体では動かしていません（未検証）。同じ SQL を DuckDB で実行しています（src/a410_abc.py）
-- sales(商品ID, 年, 月, 売上)。@from・@to で期間を、@a・@b で区切りを変える

DECLARE @from INT = 202501, @to INT = 202512, @a FLOAT = 0.70, @b FLOAT = 0.90;

WITH y AS (
  SELECT 商品ID, SUM(売上) AS 売上
  FROM dbo.sales
  WHERE 年 * 100 + 月 BETWEEN @from AND @to
  GROUP BY 商品ID
),
c AS (
  SELECT 商品ID, 売上,
         -- 同じ売上の商品があっても順が決まるよう、商品ID も並びに入れる。枠は ROWS で書く
         SUM(売上) OVER (ORDER BY 売上 DESC, 商品ID
                         ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) - 売上 AS 上の累計,
         SUM(売上) OVER () AS 全体
  FROM y
)
SELECT 商品ID, 売上,
       CASE WHEN 1.0 * 上の累計 / 全体 < @a THEN 'A'
            WHEN 1.0 * 上の累計 / 全体 < @b THEN 'B'
            ELSE 'C' END AS ランク
FROM c;

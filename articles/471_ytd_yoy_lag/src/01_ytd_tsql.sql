-- 471 年初からの累計の前年比（T-SQL の書き方。SQL Server 本体では動かしていない＝未検証。同じ文を DuckDB で実行して確かめた）
-- monthly(ym DATE, sales FLOAT)  1か月1行
WITH m AS (
  SELECT ym, YEAR(ym) AS yr, MONTH(ym) AS mon, sales,
         SUM(sales) OVER (PARTITION BY YEAR(ym) ORDER BY ym
                          ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS ytd,      -- 年初からの累計
         SUM(sales) OVER (ORDER BY ym ROWS BETWEEN 11 PRECEDING AND CURRENT ROW) AS r12, -- 直近12か月の合計
         COUNT(*)   OVER (ORDER BY ym ROWS BETWEEN 11 PRECEDING AND CURRENT ROW) AS n12
  FROM monthly
)
SELECT a.ym,
       a.sales / b.sales - 1 AS yoy_month,   -- 単月の前年同月比
       a.ytd   / b.ytd   - 1 AS yoy_ytd,     -- 年初からの累計の前年比
       CASE WHEN a.n12 = 12 AND b.n12 = 12 THEN a.r12 / b.r12 - 1 END AS yoy_r12  -- 直近12か月の合計の前年比
FROM m a
JOIN m b ON b.yr = a.yr - 1 AND b.mon = a.mon   -- LAG(…,12) ではなく、年と月でつなぐ（月が抜けてもずれない）
ORDER BY a.ym;

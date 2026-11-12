-- 481 月末締めと20日締めで月に集計する（T-SQL 版。SQL Server では動かしていない：未検証）
-- daily_sales(d date, sales bigint)
-- 20日締めの「月」= (日付 - 20日) の月の翌月。3月21日 → 4月分、3月20日 → 3月分
WITH t AS (
    SELECT d, sales,
           DATEFROMPARTS(YEAR(d), MONTH(d), 1)                                  AS m_end,
           DATEADD(month, 1, DATEFROMPARTS(YEAR(DATEADD(day, -20, d)),
                                           MONTH(DATEADD(day, -20, d)), 1))      AS m_20
    FROM daily_sales
)
SELECT a.m, a.v AS month_end, b.v AS close20, a.n AS days_end, b.n AS days_20
FROM (SELECT m_end AS m, SUM(sales) AS v, COUNT(*) AS n FROM t GROUP BY m_end) AS a
JOIN (SELECT m_20  AS m, SUM(sales) AS v, COUNT(*) AS n FROM t GROUP BY m_20)  AS b
  ON a.m = b.m
ORDER BY a.m;

-- 前年同月比（どちらの締めでも同じ形）
-- SELECT m, close20, 100.0 * close20 / LAG(close20, 12) OVER (ORDER BY m) - 100 AS yoy_20 FROM monthly;
-- 注意：LAG(…,12) は月が1つも抜けていない前提（232 参照）

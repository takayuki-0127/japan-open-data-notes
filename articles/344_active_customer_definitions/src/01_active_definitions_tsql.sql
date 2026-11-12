-- 344 「アクティブな顧客」を5つの定義で数える（T-SQL 版。SQL Server 本体では動かしていません＝未検証）
-- buy(cust INT, d DATE) / login(cust INT, d DATE) / me(me DATE)＝月末の日付
SELECT me.me,
  (SELECT COUNT(DISTINCT cust) FROM buy   WHERE d >  DATEADD(DAY, -30, me.me) AND d <= me.me) AS d1_buy30,
  (SELECT COUNT(DISTINCT cust) FROM buy   WHERE d >  DATEADD(DAY, -90, me.me) AND d <= me.me) AS d2_buy90,
  (SELECT COUNT(DISTINCT cust) FROM buy   WHERE d >= DATEFROMPARTS(YEAR(me.me), MONTH(me.me), 1) AND d <= me.me) AS d3_buy_month,
  (SELECT COUNT(DISTINCT cust) FROM login WHERE d >  DATEADD(DAY, -30, me.me) AND d <= me.me) AS d4_login30,
  (SELECT COUNT(*) FROM (SELECT cust FROM buy WHERE d > DATEADD(DAY, -90, me.me) AND d <= me.me
                         GROUP BY cust HAVING COUNT(*) >= 2) AS t) AS d5_buy90_twice
FROM me ORDER BY me.me;

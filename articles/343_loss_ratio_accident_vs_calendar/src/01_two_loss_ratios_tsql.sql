-- 343 損害率を2つの数え方で出す（T-SQL 版。SQL Server 本体では動かしていません＝未検証）
-- premium(year INT, earned_premium DECIMAL(18,2)) / claims(claim_id INT, acc_year INT, ultimate DECIMAL(18,2))
-- payments(claim_id INT, pay_year INT, paid DECIMAL(18,2))
-- 1) 支払った年で数える
SELECT p.year, SUM(y.paid) / MAX(p.earned_premium) AS lr_calendar
FROM premium AS p LEFT JOIN payments AS y ON y.pay_year = p.year
GROUP BY p.year ORDER BY p.year;

-- 2) 事故が起きた年で数える（@asof 年までに払った分と、払い終わった分）
DECLARE @asof INT = 2025;
SELECT p.year,
       SUM(CASE WHEN y.pay_year <= @asof THEN y.paid ELSE 0 END) / MAX(p.earned_premium) AS lr_accident_to_date,
       SUM(y.paid) / MAX(p.earned_premium)                                               AS lr_accident
FROM premium AS p
LEFT JOIN claims   AS c ON c.acc_year = p.year
LEFT JOIN payments AS y ON y.claim_id = c.claim_id
GROUP BY p.year ORDER BY p.year;

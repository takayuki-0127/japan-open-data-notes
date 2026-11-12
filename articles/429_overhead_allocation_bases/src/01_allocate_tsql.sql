-- 429 共通の費用を部門に配る（T-SQL 版。SQL Server 本体では未検証）
-- dept(dept varchar(10), sales bigint, direct_profit bigint, headcount int, area_m2 int, it_hours int)
-- shared(cost_name varchar(10), amount bigint)   … 本社費・施設費・システム費

-- ① 共通費の合計を、1つの基準（ここでは人数）で配る
WITH t AS (SELECT SUM(amount) AS total FROM shared)
SELECT d.dept,
       d.direct_profit,
       t.total * d.headcount * 1.0 / SUM(d.headcount) OVER () AS allocated,
       d.direct_profit - t.total * d.headcount * 1.0 / SUM(d.headcount) OVER () AS profit_after
FROM dept d CROSS JOIN t;

-- ② 費用ごとに基準を変えて配る（本社費＝人数、施設費＝面積、システム費＝使った時間）
SELECT d.dept,
       d.direct_profit
       - SUM(CASE s.cost_name
               WHEN '本社費'     THEN s.amount * d.headcount * 1.0 / x.headcount
               WHEN '施設費'     THEN s.amount * d.area_m2  * 1.0 / x.area_m2
               WHEN 'システム費' THEN s.amount * d.it_hours * 1.0 / x.it_hours
             END) AS profit_after
FROM dept d
CROSS JOIN shared s
CROSS JOIN (SELECT SUM(headcount) AS headcount, SUM(area_m2) AS area_m2, SUM(it_hours) AS it_hours FROM dept) x
GROUP BY d.dept, d.direct_profit;

-- 495：会員ランクを「暦年」と「直近12か月」で判定する（T-SQL、未検証：SQL Server では動かしていない）
-- monthly_spend(member, ym DATE（月初）, amount)
DECLARE @asof DATE = '2025-12-01';
WITH cal AS (           -- 暦年：前の年の1〜12月
    SELECT member, SUM(amount) AS y
    FROM monthly_spend WHERE ym >= DATEFROMPARTS(YEAR(@asof) - 1, 1, 1) AND ym < DATEFROMPARTS(YEAR(@asof), 1, 1)
    GROUP BY member),
roll AS (               -- 直近12か月：判定日の前の月までの12か月
    SELECT member, SUM(amount) AS r12
    FROM monthly_spend WHERE ym >= DATEADD(MONTH, -12, @asof) AND ym < @asof
    GROUP BY member)
SELECT COALESCE(c.member, r.member) AS member,
       CASE WHEN c.y   >= 100000 THEN N'ゴールド' WHEN c.y   >= 30000 THEN N'シルバー' ELSE N'ブロンズ' END AS rank_calendar,
       CASE WHEN r.r12 >= 100000 THEN N'ゴールド' WHEN r.r12 >= 30000 THEN N'シルバー' ELSE N'ブロンズ' END AS rank_rolling
FROM cal c FULL OUTER JOIN roll r ON r.member = c.member;

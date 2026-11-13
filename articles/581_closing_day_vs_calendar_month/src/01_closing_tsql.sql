-- 締め日20日：前月21日〜当月20日を「当月」として売上を数える（T-SQL、未検証）
-- 21日以降の取引は、翌月の締め期間に入れる。月は「その月の1日」で表す
SELECT
  DATEFROMPARTS(YEAR(c.close_d), MONTH(c.close_d), 1) AS close_m,
  SUM(t.amount) AS sales
FROM dbo.transactions AS t
CROSS APPLY (
  SELECT CASE WHEN DAY(t.sold_on) <= 20 THEN t.sold_on
              ELSE DATEADD(MONTH, 1, t.sold_on) END AS close_d
) AS c
WHERE t.sold_on BETWEEN '2022-12-21' AND '2025-12-20'
GROUP BY DATEFROMPARTS(YEAR(c.close_d), MONTH(c.close_d), 1)
ORDER BY close_m;

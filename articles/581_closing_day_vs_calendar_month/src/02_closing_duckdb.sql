-- 締め日20日：前月21日〜当月20日を「当月」として売上を数える（DuckDB）
-- 21日以降の取引は、翌月の締め期間に入れる
SELECT
  CASE WHEN DAY(sold_on) <= 20
       THEN DATE_TRUNC('month', sold_on)
       ELSE DATE_TRUNC('month', sold_on) + INTERVAL 1 MONTH
  END AS close_m,
  SUM(amount) AS sales
FROM transactions
WHERE sold_on BETWEEN DATE '2022-12-21' AND DATE '2025-12-20'
GROUP BY 1
ORDER BY 1;

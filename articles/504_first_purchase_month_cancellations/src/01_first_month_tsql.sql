-- T-SQL 版（SQL Server では動かしていない：未検証）
-- 初回購入月は、確定の注文だけ（取消・返品・テスト用の会員を除く）で決める
WITH f AS (
  SELECT o.member_id, MIN(o.ordered_at) AS first_at
  FROM dbo.orders AS o
  JOIN dbo.members AS m ON m.member_id = o.member_id AND m.is_test = 0
  WHERE o.status = N'確定' AND o.is_deleted = 0
  GROUP BY o.member_id
)
SELECT DATEFROMPARTS(YEAR(first_at), MONTH(first_at), 1) AS first_month, COUNT(*) AS new_customers
FROM f
GROUP BY DATEFROMPARTS(YEAR(first_at), MONTH(first_at), 1)
ORDER BY first_month;
-- 注意：返品をあとから「確定」に戻すなど、状態が変わる運用では、いつの時点の状態で決めたかも残す（342 を参照）

-- 判定日（2025-06-30）時点で、最終購入から90日・180日を超えた会員を数える（DuckDB）
WITH last_buy AS (
  SELECT member_id, MAX(bought_on) AS last_on
  FROM purchases
  WHERE bought_on <= DATE '2025-06-30'
  GROUP BY member_id
)
SELECT COUNT(*) FILTER (WHERE DATE '2025-06-30' - last_on > 90)  AS dormant_90,
       COUNT(*) FILTER (WHERE DATE '2025-06-30' - last_on > 180) AS dormant_180,
       COUNT(*) AS members
FROM last_buy;

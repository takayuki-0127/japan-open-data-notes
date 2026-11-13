-- 平均の購入間隔（DuckDB 版）。purchases(customer_id, bought_on)、customers(customer_id, registered_on)、観察の終わりは 2025-12-31
-- (1) 2回以上買った人の、購入と購入のあいだの日数の平均（よくある出し方）
WITH g AS (
  SELECT customer_id,
         bought_on - LAG(bought_on) OVER (PARTITION BY customer_id ORDER BY bought_on) AS gap
  FROM purchases)
SELECT AVG(gap) AS mean_gap_2plus, COUNT(DISTINCT customer_id) AS customers_2plus
FROM g WHERE gap IS NOT NULL;
-- (2) 見ていた日数の合計 ÷ 購入回数の合計（最後の購入から観察の終わりまでも数に入れる）
SELECT (SELECT SUM(DATE '2025-12-31' - registered_on) FROM customers) * 1.0
       / (SELECT COUNT(*) FROM purchases) AS days_per_purchase;

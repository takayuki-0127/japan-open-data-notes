-- DuckDB で実行（1スレッド）。:th は Python から金額の基準（円）を差し込む
WITH big_order AS (          -- 1回 :th 円以上の注文がある顧客（WHERE で行を絞ってから）
    SELECT DISTINCT customer_id FROM orders WHERE amount >= :th
), big_total AS (            -- 合計 :th 円以上の顧客（集計してから HAVING）
    SELECT customer_id FROM orders GROUP BY customer_id HAVING SUM(amount) >= :th
), wrong_sales AS (          -- まちがい：WHERE で行を絞ってから合計し、HAVING をかける
    SELECT customer_id, SUM(amount) AS s FROM orders WHERE amount >= :th GROUP BY customer_id HAVING SUM(amount) >= :th
)
SELECT
    (SELECT COUNT(*) FROM big_order)                                                      AS n_big_order,
    (SELECT COUNT(*) FROM big_total)                                                      AS n_big_total,
    (SELECT COUNT(*) FROM big_order WHERE customer_id IN (SELECT customer_id FROM big_total)) AS n_both,
    (SELECT SUM(amount) FROM orders WHERE customer_id IN (SELECT customer_id FROM big_total)) AS sales_big_total,
    (SELECT SUM(s) FROM wrong_sales)                                                      AS sales_wrong;

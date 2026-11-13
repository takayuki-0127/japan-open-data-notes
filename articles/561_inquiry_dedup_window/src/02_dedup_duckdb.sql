-- 同じ人の直前の問い合わせから :window_sec 秒以内なら同じ件とみなして、件数を数える（DuckDB）
-- :same_cat = 1 のときは、直前と同じ分類のときだけまとめる
WITH s AS (
  SELECT *,
         LAG(received_at) OVER (PARTITION BY customer_id ORDER BY received_at, inquiry_id) AS prev_t,
         LAG(category)    OVER (PARTITION BY customer_id ORDER BY received_at, inquiry_id) AS prev_cat
  FROM inquiries),
f AS (
  SELECT *,
         CASE WHEN prev_t IS NOT NULL
               AND date_diff('second', prev_t, received_at) <= :window_sec
               AND (:same_cat = 0 OR category = prev_cat)
              THEN 0 ELSE 1 END AS is_new
  FROM s)
SELECT SUM(is_new) AS cases FROM f;

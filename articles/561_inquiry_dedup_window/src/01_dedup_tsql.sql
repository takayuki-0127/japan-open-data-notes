-- 同じ人の直前の問い合わせから @window_sec 秒以内なら同じ件とみなす（T-SQL、SQL Server では未検証）
DECLARE @window_sec int = 600;   -- 10分
DECLARE @same_cat   bit = 0;     -- 1 なら同じ分類のときだけまとめる
WITH s AS (
  SELECT *,
         LAG(received_at) OVER (PARTITION BY customer_id ORDER BY received_at, inquiry_id) AS prev_t,
         LAG(category)    OVER (PARTITION BY customer_id ORDER BY received_at, inquiry_id) AS prev_cat
  FROM dbo.inquiries),
f AS (
  SELECT *,
         CASE WHEN prev_t IS NOT NULL
               AND DATEDIFF(second, prev_t, received_at) <= @window_sec
               AND (@same_cat = 0 OR category = prev_cat)
              THEN 0 ELSE 1 END AS is_new
  FROM s),
g AS (  -- 件の番号：is_new を足し上げる
  SELECT *, SUM(is_new) OVER (PARTITION BY customer_id ORDER BY received_at, inquiry_id
                              ROWS UNBOUNDED PRECEDING) AS case_no
  FROM f)
SELECT COUNT(DISTINCT CONCAT(customer_id, '-', case_no)) AS cases FROM g;

-- DuckDB で実行（1スレッド）。最初・最新・ある日時点の3通りで1顧客1行にして、ランク別に数える
WITH r AS (
    SELECT *,
           ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY updated_at ASC,  row_id ASC)  AS rn_first,
           ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY updated_at DESC, row_id DESC) AS rn_last
    FROM customers_raw
), a AS (
    SELECT *,
           ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY updated_at DESC, row_id DESC) AS rn_asof
    FROM customers_raw
    WHERE updated_at <= DATE '2024-12-31'
)
SELECT 'raw'   AS method, member_rank, COUNT(*) AS customers FROM customers_raw GROUP BY member_rank
UNION ALL
SELECT 'first', member_rank, COUNT(*) FROM r WHERE rn_first = 1 GROUP BY member_rank
UNION ALL
SELECT 'last',  member_rank, COUNT(*) FROM r WHERE rn_last  = 1 GROUP BY member_rank
UNION ALL
SELECT 'asof',  member_rank, COUNT(*) FROM a WHERE rn_asof  = 1 GROUP BY member_rank
ORDER BY method, member_rank;

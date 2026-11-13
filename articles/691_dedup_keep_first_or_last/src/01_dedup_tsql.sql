-- T-SQL：未検証（SQL Server では動かしていない）
-- 同じ顧客の重複行から「最新」を1行残す
WITH ranked AS (
    SELECT c.*,
           ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY updated_at DESC, row_id DESC) AS rn
    FROM customers_raw AS c
)
SELECT customer_id, region, member_rank, updated_at
FROM ranked
WHERE rn = 1;

-- 「最初」を残す場合は ORDER BY updated_at ASC, row_id ASC
-- ある日（例：2024-12-31）時点の属性は、その日までに更新された行の中で最新を残す
WITH asof AS (
    SELECT c.*,
           ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY updated_at DESC, row_id DESC) AS rn
    FROM customers_raw AS c
    WHERE updated_at <= '2024-12-31'
)
SELECT member_rank, COUNT(*) AS customers
FROM asof
WHERE rn = 1
GROUP BY member_rank;

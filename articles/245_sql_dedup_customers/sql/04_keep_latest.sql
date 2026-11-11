-- 04 グループごとに1行残す（T-SQL と DuckDB で同じ文。DuckDB で検証。dbo.groups は 03 の結果を入れた表）
-- 新しい行を残すが、新しい行で空の電話は、同じグループの古い行から埋める
WITH k AS (
    SELECT g.*, c.name, c.birth, c.email,
           ROW_NUMBER() OVER (PARTITION BY g.g5 ORDER BY g.updated_at DESC, g.customer_id DESC) AS rn,
           FIRST_VALUE(g.tel) OVER (PARTITION BY g.g5
               ORDER BY CASE WHEN g.tel IS NULL THEN 1 ELSE 0 END, g.updated_at DESC
               ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING)        AS tel_filled
    FROM dbo.groups AS g
    JOIN dbo.customers AS c ON c.customer_id = g.customer_id
)
SELECT g5 AS group_id, customer_id AS kept_id, name, birth, email, tel AS tel_latest, tel_filled
FROM k
WHERE rn = 1;

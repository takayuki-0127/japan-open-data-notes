-- T-SQL：未検証（SQL Server では動かしていない）
-- 0 先に重複を調べる
SELECT customer_id, COUNT(*) AS n FROM dbo.updates GROUP BY customer_id HAVING COUNT(*) > 1;
-- 最新の1行に絞ってから MERGE
WITH src AS (
  SELECT customer_id, rank_code, updated_at,
         ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY updated_at DESC, file_row DESC) AS k
  FROM dbo.updates)
MERGE dbo.customers AS c
USING (SELECT customer_id, rank_code, updated_at FROM src WHERE k = 1) AS u
   ON c.customer_id = u.customer_id
WHEN MATCHED THEN UPDATE SET rank_code = u.rank_code, updated_at = u.updated_at
WHEN NOT MATCHED THEN INSERT (customer_id, rank_code, updated_at) VALUES (u.customer_id, u.rank_code, u.updated_at);
-- 絞らずに MERGE すると、同じ行が複数の元の行と合うためエラーになるとされる（未検証）

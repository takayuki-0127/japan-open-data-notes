-- 取り込み元に同じ顧客が2行ある更新ファイルで、顧客表を更新する（DuckDB 版）
-- customers(customer_id PRIMARY KEY, rank_code, updated_at)、updates(file_row, customer_id, rank_code, updated_at)
-- 0 先に重複を調べる
SELECT COUNT(*) AS dup_customers
FROM (SELECT customer_id FROM updates GROUP BY customer_id HAVING COUNT(*) > 1) d;
-- A そのまま INSERT … ON CONFLICT DO UPDATE（重複があってもエラーにならない）
INSERT INTO customers
SELECT customer_id, rank_code, updated_at FROM updates ORDER BY file_row
ON CONFLICT (customer_id) DO UPDATE SET rank_code = excluded.rank_code, updated_at = excluded.updated_at;
-- B 最新の1行に絞ってから同じ更新
INSERT INTO customers
SELECT customer_id, rank_code, updated_at
FROM (SELECT *, ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY updated_at DESC, file_row DESC) AS k FROM updates) t
WHERE k = 1
ON CONFLICT (customer_id) DO UPDATE SET rank_code = excluded.rank_code, updated_at = excluded.updated_at;
-- C MERGE（同じ行を2回更新しようとするとエラー）
MERGE INTO customers c USING updates u ON c.customer_id = u.customer_id
WHEN MATCHED THEN UPDATE SET rank_code = u.rank_code, updated_at = u.updated_at
WHEN NOT MATCHED THEN INSERT VALUES (u.customer_id, u.rank_code, u.updated_at);

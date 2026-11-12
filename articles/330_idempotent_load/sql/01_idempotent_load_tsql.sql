-- 330 やり直しても同じ結果になる取り込み（T-SQL 版）。SQL Server 本体では動かしていません（未検証。MERGE は T-SQL の命令）。
-- 同じ流れを DuckDB（INSERT … ON CONFLICT）で動かしたものは src/a330_idempotent.py にあります。
-- stg がその回に届いたファイルの中身、sales が取り込み先。キーは (sales_date, store_id, item_id)

-- A 追記だけ
INSERT INTO sales SELECT sales_date, store_id, item_id, qty, amount, file_version FROM stg;

-- B その日の分を洗い替え（1つのトランザクション）
BEGIN TRAN;
DELETE FROM sales WHERE sales_date IN (SELECT DISTINCT sales_date FROM stg);
INSERT INTO sales SELECT sales_date, store_id, item_id, qty, amount, file_version FROM stg;
COMMIT;

-- C キーで上書き
MERGE sales AS t USING stg AS s
   ON t.sales_date = s.sales_date AND t.store_id = s.store_id AND t.item_id = s.item_id
WHEN MATCHED THEN UPDATE SET qty = s.qty, amount = s.amount, file_version = s.file_version
WHEN NOT MATCHED THEN INSERT (sales_date, store_id, item_id, qty, amount, file_version)
     VALUES (s.sales_date, s.store_id, s.item_id, s.qty, s.amount, s.file_version);

-- E キーで上書き＋版の比較＋古い版の行を消す（1つのトランザクション）
BEGIN TRAN;
MERGE sales AS t USING stg AS s
   ON t.sales_date = s.sales_date AND t.store_id = s.store_id AND t.item_id = s.item_id
WHEN MATCHED AND s.file_version >= t.file_version                       -- 古い版では上書きしない
     THEN UPDATE SET qty = s.qty, amount = s.amount, file_version = s.file_version
WHEN NOT MATCHED THEN INSERT (sales_date, store_id, item_id, qty, amount, file_version)
     VALUES (s.sales_date, s.store_id, s.item_id, s.qty, s.amount, s.file_version);
DELETE t FROM sales t                                                    -- 新しい版に出てこなかった行（取り消し）を消す
JOIN (SELECT sales_date, MAX(file_version) AS v FROM stg GROUP BY sales_date) f ON f.sales_date = t.sales_date
WHERE t.file_version < f.v;
COMMIT;

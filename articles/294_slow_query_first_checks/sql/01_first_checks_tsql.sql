-- SQL Server で「遅いクエリ」をまず見る手順（T-SQL。この記事では SQL Server 本体では試していない＝未検証）
-- 1) 読んだページ数と時間を出す
SET STATISTICS IO ON;  SET STATISTICS TIME ON;
-- 2) 実際の実行プランを出す（SSMS の「実際の実行プランを含める」でも同じ）
SET STATISTICS XML ON;
SELECT COUNT(*), SUM(amount) FROM dbo.orders WHERE customer_id = 12345;
SET STATISTICS XML OFF;
-- 見るところ：Table Scan / Clustered Index Scan（全部読む）か Index Seek（絞って読む）か、
--            Key Lookup（本体へ取りに戻る）が多くないか、推定行数と実際の行数が大きくずれていないか

-- 場面1 索引がない → 絞り込む列に索引
CREATE INDEX ix_cust ON dbo.orders(customer_id);
-- 場面2 列に関数をかけている → 範囲の条件に書き直す
--   遅い：WHERE FORMAT(order_date, 'yyyy-MM') = '2025-03'  /  WHERE YEAR(order_date) = 2025
SELECT COUNT(*), SUM(amount) FROM dbo.orders WHERE order_date >= '2025-03-01' AND order_date < '2025-04-01';
-- 場面3 複合索引は「等号の列 → 範囲の列」の順
CREATE INDEX ix_store_date ON dbo.orders(store_id, order_date);
-- 場面4 本体へ取りに戻らないよう、使う列を INCLUDE に入れる（Key Lookup をなくす）
CREATE INDEX ix_store_date_amt ON dbo.orders(store_id, order_date) INCLUDE (amount);
-- 場面5 ほとんどの行が当てはまる条件は、索引より全部読むほうが速い。統計情報を新しくして、オプティマイザに任せる
UPDATE STATISTICS dbo.orders;

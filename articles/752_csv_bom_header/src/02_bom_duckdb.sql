-- BOM つき・なしの CSV が混ざったフォルダを DuckDB で読む（DuckDB 版）
-- 列名を確かめる（先頭の列名が store_id になっているか）
SELECT column_name FROM (DESCRIBE SELECT * FROM read_csv('{DATA}/sales_2025*.csv', union_by_name = true));
-- 2年分を読んで合計（BOM は外して読まれる）
SELECT SUM(sales) AS total FROM read_csv('{DATA}/sales_20*.csv', union_by_name = true);
-- 店のマスタと結べない行を数える（結べない行があれば列名やキーを疑う）
SELECT COUNT(*) AS unmatched
FROM read_csv('{DATA}/sales_20*.csv', union_by_name = true) s
LEFT JOIN read_csv('{DATA}/stores.csv') m USING (store_id)
WHERE m.area IS NULL;

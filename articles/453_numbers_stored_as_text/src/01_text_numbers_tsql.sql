-- 453 数字が文字として入った列の並べ替え・MAX・BETWEEN（T-SQL 版）
-- 未検証：SQL Server 本体では動かしていません。同じ考え方の SQL を DuckDB で実行しました（a453_text_numbers.py）。
-- 文字の大小は照合順序（collation）で変わります。SQL Server の照合順序での並びは確かめていません。
-- 前提：dbo.slips(row_id int, customer int, slip_no varchar(10), branch varchar(3), amount varchar(12))

-- 文字のまま（誤りやすい）
SELECT TOP (10) amount FROM dbo.slips ORDER BY amount DESC;
SELECT customer, MAX(amount) AS max_text FROM dbo.slips GROUP BY customer;
SELECT COUNT(*) FROM dbo.slips WHERE amount BETWEEN '5000' AND '20000';   -- '5000' > '20000' なので0件

-- 数に直してから
SELECT TOP (10) amount FROM dbo.slips ORDER BY TRY_CAST(amount AS bigint) DESC;
SELECT customer, MAX(TRY_CAST(amount AS bigint)) AS max_num FROM dbo.slips GROUP BY customer;
SELECT COUNT(*) FROM dbo.slips WHERE TRY_CAST(amount AS bigint) BETWEEN 5000 AND 20000;

-- 数に直せない行がないかを先に数える（カンマ入り・小数・空白など）
SELECT COUNT(*) AS not_converted
FROM dbo.slips
WHERE amount IS NOT NULL AND TRY_CAST(REPLACE(amount, ',', '') AS decimal(12, 1)) IS NULL;

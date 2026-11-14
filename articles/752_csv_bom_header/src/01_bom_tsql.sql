-- T-SQL：未検証（SQL Server では動かしていない）
-- UTF-8 の CSV を取り込むときは CODEPAGE を指定する。見出し行は FIRSTROW = 2 で飛ばす
BULK INSERT dbo.sales_stage
FROM 'C:\data\sales_202504.csv'
WITH (FORMAT = 'CSV', CODEPAGE = '65001', FIRSTROW = 2, FIELDTERMINATOR = ',', ROWTERMINATOR = '0x0a');
-- 取り込んだあと、店のマスタと結べない行を数える
SELECT COUNT(*) AS unmatched
FROM dbo.sales_stage s
LEFT JOIN dbo.stores m ON m.store_id = s.store_id
WHERE m.area IS NULL;
-- 先頭の値に見えない文字が残っていないか（BOM が値に入ると長さが1増える）
SELECT TOP 5 store_id, LEN(store_id) AS len_chars, UNICODE(LEFT(store_id, 1)) AS first_code
FROM dbo.sales_stage ORDER BY LEN(store_id) DESC;

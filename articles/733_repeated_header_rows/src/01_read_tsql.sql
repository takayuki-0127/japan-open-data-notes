-- T-SQL：未検証（SQL Server では動かしていない）
-- 1本ずつ BULK INSERT し、見出し行は FIRSTROW = 2 で飛ばす。列の順が違うファイルは、別の書式で読む必要がある
BULK INSERT dbo.sales_stage
FROM 'C:\data\monthly_01.csv'
WITH (FIRSTROW = 2, FIELDTERMINATOR = ',', ROWTERMINATOR = '0x0a', CODEPAGE = '65001');

-- 縦につないだファイルを読んでしまったときの確認：見出しの文字列が値に入った行を探す
SELECT COUNT(*) AS header_rows
FROM dbo.sales_stage_raw
WHERE sales_date = 'sales_date' OR amount = 'amount';

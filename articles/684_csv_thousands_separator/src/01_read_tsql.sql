-- T-SQL：未検証
-- 引用符ありの CSV を読み込み、金額の「,」を除いてから数にする（SQL Server 2017 以降の FORMAT = 'CSV'）
CREATE TABLE #raw (date varchar(10), store nvarchar(10), item nvarchar(10), amount varchar(20), qty int);
BULK INSERT #raw FROM 'C:\data\sales_quoted.csv'
WITH (FORMAT = 'CSV', FIELDQUOTE = '"', FIRSTROW = 2, CODEPAGE = '65001');

SELECT SUM(CAST(REPLACE(amount, ',', '') AS bigint)) AS amount_sum FROM #raw;

-- 書き出す側：金額は FORMAT(amount, 'N0') などで桁区切りにせず、数のまま出す

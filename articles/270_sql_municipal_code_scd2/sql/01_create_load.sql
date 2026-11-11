-- 01 表を作る（T-SQL）。読み込みは BULK INSERT（SQL Server では未検証。DuckDB では read_csv で同じ表を作る）
CREATE TABLE dbo.units2000 (code CHAR(5) PRIMARY KEY, name NVARCHAR(40), pop2000 INT);      -- 2000年10月1日の3,252単位
CREATE TABLE dbo.units2020 (code CHAR(5) PRIMARY KEY, name NVARCHAR(40), pop2020 INT);      -- 2020年の1,741単位
CREATE TABLE dbo.events_x (                       -- 廃置分合を「旧コード1つ」ずつの行にばらしたもの
    eff_date DATE, kind NVARCHAR(10), old_code CHAR(5), new_code CHAR(5), new_name NVARCHAR(40));
-- BULK INSERT dbo.events_x FROM 'events_x.csv' WITH (FIRSTROW = 2, FIELDTERMINATOR = ',', CODEPAGE = '65001');

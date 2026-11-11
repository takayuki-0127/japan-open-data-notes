-- 01 取り込み（T-SQL）。BULK INSERT は SQL Server 専用のため、この記事の環境では未検証
CREATE TABLE dbo.sales_monthly (
    gyotai  NVARCHAR(20) NOT NULL,   -- 業態
    ym      DATE         NOT NULL,   -- 月（その月の1日）
    sales   BIGINT       NOT NULL,   -- 販売額（百万円）
    CONSTRAINT PK_sales_monthly PRIMARY KEY (gyotai, ym)
);
BULK INSERT dbo.sales_monthly
FROM 'C:\data\meti_sales_monthly.csv'
WITH (FIRSTROW = 2, FIELDTERMINATOR = ',', ROWTERMINATOR = '0x0a', CODEPAGE = '65001');

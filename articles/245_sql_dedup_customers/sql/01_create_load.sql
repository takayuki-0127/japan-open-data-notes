-- 01 取り込み（T-SQL）。BULK INSERT は SQL Server 専用のため、この記事の環境では未検証
CREATE TABLE dbo.customers (
    customer_id INT           NOT NULL PRIMARY KEY,
    person_id   INT           NOT NULL,   -- 正解の人ID（架空データなので分かる。実務の表にはない）
    name        NVARCHAR(40)  NOT NULL,
    birth       DATE          NOT NULL,
    tel         VARCHAR(20)   NULL,
    email       VARCHAR(100)  NOT NULL,
    dup_type    NVARCHAR(20)  NOT NULL,   -- 重複の種類（説明用）
    updated_at  DATETIME2     NOT NULL
);
BULK INSERT dbo.customers FROM 'C:\data\customers.csv'
WITH (FIRSTROW = 2, FIELDTERMINATOR = ',', ROWTERMINATOR = '0x0a', CODEPAGE = '65001');

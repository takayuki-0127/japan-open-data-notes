-- 491：セルの中に改行がある CSV を SQL Server に取り込む（T-SQL、未検証：SQL Server では動かしていない）
-- 既定の BULK INSERT は、行の区切り（ROWTERMINATOR）で機械的に分けるので、引用符の中の改行でも行が切れる。
-- SQL Server 2017 以降は FORMAT = 'CSV' と FIELDQUOTE で、引用符の中の改行・カンマをそのまま読める（とされる）。
CREATE TABLE stg_inquiries (
    id        INT,
    received  VARCHAR(16),
    category  NVARCHAR(10),
    body      NVARCHAR(MAX),
    amount    INT
);

-- 素朴な読み方（引用符を見ない）：本文に改行がある記録は、複数の行に割れて、列の数が合わなくなる
-- BULK INSERT stg_inquiries FROM 'C:\data\fictional_inquiries.csv'
--   WITH (FIELDTERMINATOR = ',', ROWTERMINATOR = '0x0a', FIRSTROW = 2, CODEPAGE = '65001');

-- 決まりどおりの読み方
BULK INSERT stg_inquiries FROM 'C:\data\fictional_inquiries.csv'
WITH (FORMAT = 'CSV', FIELDQUOTE = '"', FIELDTERMINATOR = ',', ROWTERMINATOR = '0x0d0a',
      FIRSTROW = 2, CODEPAGE = '65001');

-- 取り込んだあとの確かめ：件数と、改行を含む本文の数
SELECT COUNT(*) AS records,
       SUM(CASE WHEN body LIKE '%' + CHAR(10) + '%' THEN 1 ELSE 0 END) AS records_with_newline
FROM stg_inquiries;

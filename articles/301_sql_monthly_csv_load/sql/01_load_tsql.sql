-- SQL Server（T-SQL）版：毎月の CSV を取り込む形
-- ※ この記事の検証は DuckDB で行いました。この T-SQL は SQL Server 本体では動かしていません（未検証）。

-- 1) 受け皿（ステージング表）：全部の列を文字で受ける
CREATE TABLE stg_sales (gyotai NVARCHAR(50), ym NVARCHAR(20), sales NVARCHAR(50));

-- 2) 本番の表：キー（業態・年月）に主キーをつける
CREATE TABLE sales_monthly (
    gyotai NVARCHAR(50) NOT NULL, ym DATE NOT NULL, sales BIGINT NOT NULL,
    loaded_file NVARCHAR(200) NOT NULL, src_period DATE NOT NULL,   -- src_period＝何月時点の届けか
    loaded_at DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
    CONSTRAINT pk_sales_monthly PRIMARY KEY (gyotai, ym));

-- 3) はじいた行と、取り込みの記録
CREATE TABLE load_reject (loaded_file NVARCHAR(200), gyotai NVARCHAR(50), ym NVARCHAR(20), sales NVARCHAR(50), reason NVARCHAR(100));
CREATE TABLE load_log (loaded_file NVARCHAR(200), file_hash CHAR(64), rows_in INT, rows_ok INT, rows_reject INT, loaded_at DATETIME2 DEFAULT SYSDATETIME());

-- 4) 取り込み（1ファイルごと）。@file・@hash・@period（何月時点の届けか）は呼び出す側が渡す
TRUNCATE TABLE stg_sales;
BULK INSERT stg_sales FROM 'C:\in\sales_2025-06.csv'
    WITH (FORMAT = 'CSV', FIRSTROW = 2, CODEPAGE = '65001');   -- BATCHSIZE は付けない（付けると途中まで確定する）

IF EXISTS (SELECT 1 FROM load_log WHERE file_hash = @hash) RETURN;   -- 同じ中身のファイルは2回入れない

BEGIN TRAN;
    -- 型に直せない行は、はじいて記録する
    INSERT INTO load_reject (loaded_file, gyotai, ym, sales, reason)
    SELECT @file, gyotai, ym, sales, N'数字か日付に直せない'
    FROM stg_sales
    WHERE TRY_CONVERT(BIGINT, REPLACE(sales, ',', '')) IS NULL OR TRY_CONVERT(DATE, ym) IS NULL;

    -- 同じキーの古い行を消してから入れる（何度流しても同じ結果になる）
    DELETE t FROM sales_monthly AS t
    JOIN stg_sales AS s ON t.gyotai = s.gyotai AND t.ym = TRY_CONVERT(DATE, s.ym)
    WHERE TRY_CONVERT(BIGINT, REPLACE(s.sales, ',', '')) IS NOT NULL
      AND t.src_period <= @period;          -- D：すでに入っている行のほうが新しい届けなら、消さない

    INSERT INTO sales_monthly (gyotai, ym, sales, loaded_file, src_period)
    SELECT s.gyotai, TRY_CONVERT(DATE, s.ym), TRY_CONVERT(BIGINT, REPLACE(s.sales, ',', '')), @file, @period
    FROM stg_sales AS s
    WHERE TRY_CONVERT(BIGINT, REPLACE(s.sales, ',', '')) IS NOT NULL AND TRY_CONVERT(DATE, s.ym) IS NOT NULL
      AND NOT EXISTS (SELECT 1 FROM sales_monthly AS t          -- D：新しい届けの行が残っているキーには入れない
                      WHERE t.gyotai = s.gyotai AND t.ym = TRY_CONVERT(DATE, s.ym));

    INSERT INTO load_log (loaded_file, file_hash, rows_in, rows_ok, rows_reject)
    SELECT @file, @hash, COUNT(*),
           SUM(CASE WHEN TRY_CONVERT(BIGINT, REPLACE(sales, ',', '')) IS NOT NULL AND TRY_CONVERT(DATE, ym) IS NOT NULL THEN 1 ELSE 0 END),
           SUM(CASE WHEN TRY_CONVERT(BIGINT, REPLACE(sales, ',', '')) IS NULL OR TRY_CONVERT(DATE, ym) IS NULL THEN 1 ELSE 0 END)
    FROM stg_sales;
COMMIT;

-- 5) 取り込みのあとの点検：キーの重複と、月の抜け
SELECT gyotai, ym, COUNT(*) AS n FROM sales_monthly GROUP BY gyotai, ym HAVING COUNT(*) > 1;
SELECT gyotai, COUNT(*) AS months, DATEDIFF(month, MIN(ym), MAX(ym)) + 1 AS expected
FROM sales_monthly GROUP BY gyotai HAVING COUNT(*) <> DATEDIFF(month, MIN(ym), MAX(ym)) + 1;

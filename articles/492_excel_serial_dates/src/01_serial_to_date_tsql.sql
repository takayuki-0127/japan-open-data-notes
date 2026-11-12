-- 492：Excel のシリアル値（1900年基準）を日付に直す（T-SQL、未検証：SQL Server では動かしていない）
-- SQL Server の datetime は 1900-01-01 を 0 として数えるので、Excel のシリアル値とは2日ずれる（3月1日以降）。
-- 1900-03-01 以降なら、1899-12-30 から s 日後が Excel と同じ日付になる。
SELECT s,
       DATEADD(DAY, CAST(FLOOR(s) AS INT), CAST('1899-12-30' AS DATE))         AS date_excel_1900,   -- ふつうはこれ
       CAST(CAST(s AS DATETIME) AS DATE)                                       AS date_if_cast,      -- 2日ずれる
       DATEADD(DAY, CAST(FLOOR(s) AS INT), CAST('1904-01-01' AS DATE))         AS date_excel_1904    -- 1904年基準のファイル
FROM (VALUES (1.0), (59.0), (61.0), (45658.0), (45658.75)) v(s);
-- 時刻つきの値から日付だけを取るときは、四捨五入（ROUND）ではなく切り捨て（FLOOR）

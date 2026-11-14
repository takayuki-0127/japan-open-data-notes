-- T-SQL：未検証（SQL Server では動かしていない）
-- INSERT で長すぎる文字列を入れると、ふつうはエラー（String or binary data would be truncated）になる。
-- 一方、CAST / CONVERT で短い型に変えると、エラーにならずに後ろが切れる。
SELECT CAST(name AS nvarchar(20)) AS name20, COUNT(*) AS n_products
FROM dbo.products
GROUP BY CAST(name AS nvarchar(20))
HAVING COUNT(*) > 1;
-- varchar(20) は「20バイト」。日本語の照合順序（Shift_JIS 系）なら全角は2バイト、UTF-8 の照合順序なら3バイト
SELECT name, LEN(name) AS len_chars, DATALENGTH(CAST(name AS varchar(200))) AS len_bytes
FROM dbo.products
WHERE DATALENGTH(CAST(name AS varchar(200))) > 20;
-- 入れる前に、上限を超えるものを数える
SELECT COUNT(*) AS too_long FROM dbo.products_stage WHERE LEN(name) > 20;

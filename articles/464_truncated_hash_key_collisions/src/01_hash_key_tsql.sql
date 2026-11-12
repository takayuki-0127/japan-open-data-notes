-- 464 短くしたハッシュをキーにしたときの確かめ（T-SQL 版）
-- ※ SQL Server 本体では動かしていません（未検証）。結合の数は DuckDB で確かめています（a464_hash.py）。
-- 表：dbo.dim_customer(cust_key VARCHAR(30), h32 BIGINT)   … h32 は SHA-256 の先頭32ビット
--     dbo.fact_sales(cust_key VARCHAR(30), h32 BIGINT, amount INT)

-- ハッシュを作る（SHA-256 の先頭4バイト＝32ビット、先頭8バイト＝64ビット）
SELECT cust_key,
       CONVERT(BIGINT, SUBSTRING(HASHBYTES('SHA2_256', cust_key), 1, 4)) AS h32,
       CONVERT(BIGINT, SUBSTRING(HASHBYTES('SHA2_256', cust_key), 1, 8)) AS h64   -- 符号つきになる
FROM dbo.dim_customer;

-- マスタの中で、同じハッシュになったキーがないか（これが0でなければ、結合で行が増える）
SELECT h32, COUNT(*) AS n_keys
FROM dbo.dim_customer
GROUP BY h32 HAVING COUNT(*) > 1;

-- つないだあとの行数が、取引の表の行数と同じか（ぴったり比べる）
SELECT (SELECT COUNT(*) FROM dbo.fact_sales AS f JOIN dbo.dim_customer AS d ON f.h32 = d.h32)
     - (SELECT COUNT(*) FROM dbo.fact_sales) AS extra_rows;

-- 別の顧客につながった行（元のキーが残っていれば数えられる）
SELECT COUNT(*) AS wrong_rows
FROM dbo.fact_sales AS f JOIN dbo.dim_customer AS d ON f.h32 = d.h32
WHERE f.cust_key <> d.cust_key;

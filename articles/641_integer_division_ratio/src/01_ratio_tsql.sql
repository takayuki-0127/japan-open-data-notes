-- T-SQL：未検証（SQL Server では動かしていない）
-- int どうしの割り算は小数点以下が切り捨てられる
SELECT store_id, visits, purchases, returns_,
       purchases / visits                      AS r1_int,        -- ほぼ 0
       purchases * 100 / visits                AS r2_pct_int,    -- % の整数部分（切り捨て）
       purchases * 100.0 / visits              AS r3_pct,        -- 正しい
       CAST(purchases AS decimal(18, 4)) * 100 / visits AS r4_pct_dec,
       returns_ * 100 / purchases              AS ret_pct_int,
       returns_ * 100.0 / purchases            AS ret_pct
FROM dbo.store_counts;

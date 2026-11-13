-- DuckDB：/ は小数を返すので、SQL Server の int / int は // で再現する
SELECT store_id, visits, purchases, returns_,
       purchases // visits                    AS r1_int,
       purchases * 100 // visits              AS r2_pct_int,
       purchases * 100.0 / visits             AS r3_pct,
       returns_ * 100 // purchases            AS ret_pct_int,
       returns_ * 100.0 / purchases           AS ret_pct
FROM store_counts
ORDER BY store_id

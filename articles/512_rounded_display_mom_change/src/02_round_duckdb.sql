-- DuckDB の ROUND が、表示用の値をどう丸めるかを確かめる（DuckDB で実行）
-- 小数の値（DECIMAL）と、2進数の浮動小数点（DOUBLE）で、ちょうど5の値の丸めが変わるか
SELECT x,
       ROUND(CAST(x AS DECIMAL(10,4)), 2) AS round2_decimal,
       ROUND(CAST(x AS DOUBLE), 2)        AS round2_double
FROM (VALUES ('2.675'), ('1.005'), ('3.245'), ('0.125')) AS t(x);

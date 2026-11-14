-- 申込率を、小数の桁の違う DECIMAL の列に入れる（DuckDB 版）
-- stores(store_id, visitors, applications)
-- DuckDB では DECIMAL どうしの割り算は DOUBLE になる。桁が落ちるのは、決まった桁の DECIMAL に入れるとき
SELECT store_id, visitors, applications,
       applications * 1.0 / visitors                                   AS rate_double,
       CAST(applications * 1.0 / visitors AS DECIMAL(5, 2))            AS rate_dec2,   -- 比を小数2桁（0.01 きざみ＝1ポイント）
       CAST(applications * 1.0 / visitors AS DECIMAL(6, 3))            AS rate_dec3,   -- 比を小数3桁（0.1ポイントきざみ）
       CAST(applications * 1.0 / visitors AS DECIMAL(7, 4))            AS rate_dec4,   -- 比を小数4桁
       CAST(applications * 100.0 / visitors AS DECIMAL(5, 1))          AS pct_dec1     -- %で小数1桁
FROM stores
ORDER BY store_id;
-- 丸めたあとの値で並べると同じ順位がいくつできるか
SELECT rate_dec2, COUNT(*) AS n_stores
FROM (SELECT CAST(applications * 1.0 / visitors AS DECIMAL(5, 2)) AS rate_dec2 FROM stores)
GROUP BY rate_dec2 ORDER BY rate_dec2;

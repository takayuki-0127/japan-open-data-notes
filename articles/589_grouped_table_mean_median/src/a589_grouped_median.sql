-- 度数分布表（lower, upper, n）から、中央値を「階級の中は一様」とみなして補間する（DuckDB）
-- 中央値の入る階級：累積度数が全体の半分に初めて届く階級
WITH t AS (
    SELECT lower, upper, n,
           SUM(n) OVER (ORDER BY lower) AS cum,
           SUM(n) OVER ()               AS total
    FROM freq
), k AS (
    SELECT * FROM t WHERE cum >= total / 2.0 ORDER BY lower LIMIT 1
)
SELECT lower + (total / 2.0 - (cum - n)) / n * (upper - lower) AS median_interp
FROM k;
-- 中央値が「以上」の階級に入るときは upper がないので、この式は使えない

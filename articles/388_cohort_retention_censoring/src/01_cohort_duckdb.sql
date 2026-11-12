-- 388 登録月×経過月の継続の表（DuckDB で実行）。観測の終わりは 2025-12-31、1か月＝30日
-- members(会員ID, 登録月, 登録日, 退会日)：退会日は、まだ退会していなければ NULL
WITH k AS (SELECT UNNEST(RANGE(1, 24)) AS k),
m AS (
  SELECT m.登録月, k.k,
         -- k か月後の日が、観測の終わりまでに来ているか
         CASE WHEN m.登録日 + CAST(30 * k.k AS INTEGER) <= DATE '2025-12-31' THEN 1 ELSE 0 END AS seen,
         -- その日に会員だったか（観測できた人だけ）
         CASE WHEN m.登録日 + CAST(30 * k.k AS INTEGER) <= DATE '2025-12-31'
               AND (m.退会日 IS NULL OR m.退会日 > m.登録日 + CAST(30 * k.k AS INTEGER)) THEN 1 ELSE 0 END AS alive
  FROM members AS m CROSS JOIN k
)
SELECT 登録月, k,
       COUNT(*)   AS 人数,
       SUM(seen)  AS 観測できた人数,
       SUM(alive) AS 続いていた人数
FROM m
GROUP BY 登録月, k
ORDER BY 登録月, k;
-- 継続率 = 続いていた人数 ÷ 観測できた人数。÷ 人数 にすると、観測できていない人を「辞めた」と数えることになる

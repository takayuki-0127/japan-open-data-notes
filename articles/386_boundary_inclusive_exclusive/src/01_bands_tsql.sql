-- 386 区分表につなぐ（T-SQL。SQL Server 本体では動かしていません＝未検証。同じ形を DuckDB で実行して確かめました）
-- band(no, lo, hi)：lo は「以上」、hi は「未満」。いちばん下の lo と、いちばん上の hi は NULL
-- 例：(0, NULL, 3000) (1, 3000, 5000) (2, 5000, 10000) (3, 10000, 30000) (4, 30000, NULL)

-- 正しい形：「lo 以上 hi 未満」
SELECT c.チャージID, c.金額, b.no
FROM charges AS c
LEFT JOIN band AS b
  ON (b.lo IS NULL OR c.金額 >= b.lo)
 AND (b.hi IS NULL OR c.金額 <  b.hi);

-- 取り違え①：>= を > に（境目ちょうどの行は、どの区分にも入らない。INNER JOIN なら行が消える）
--   ON (b.lo IS NULL OR c.金額 >  b.lo) AND (b.hi IS NULL OR c.金額 <  b.hi)
-- 取り違え②：<  を <= に（BETWEEN lo AND hi と同じ。境目ちょうどの行は2つの区分に入り、行が増える）
--   ON (b.lo IS NULL OR c.金額 >= b.lo) AND (b.hi IS NULL OR c.金額 <= b.hi)
-- 取り違え③：両方（境目ちょうどの行は、1つ下の区分に入る。行数は変わらない）
--   ON (b.lo IS NULL OR c.金額 >  b.lo) AND (b.hi IS NULL OR c.金額 <= b.hi)

-- つないだ後の照合：行数が元と同じか、区分のつかない行がないか、2つの区分に入った行がないか
SELECT COUNT(*)                                        AS つないだ後の行,
       (SELECT COUNT(*) FROM charges)                  AS 元の行,
       SUM(CASE WHEN b.no IS NULL THEN 1 ELSE 0 END)   AS どの区分にも入らない
FROM charges AS c
LEFT JOIN band AS b
  ON (b.lo IS NULL OR c.金額 >= b.lo)
 AND (b.hi IS NULL OR c.金額 <  b.hi);

-- 境目のテスト：境目ちょうどと、その1つ下の値が、決めた区分に入るか（期待する区分を表に持つ）
-- boundary_test(金額, 期待する区分)：(2999,0) (3000,1) (4999,1) (5000,2) (9999,2) (10000,3) (29999,3) (30000,4)
SELECT t.金額, t.期待する区分, COUNT(b.no) AS 入った区分の数, MIN(b.no) AS 入った区分
FROM boundary_test AS t
LEFT JOIN band AS b
  ON (b.lo IS NULL OR t.金額 >= b.lo)
 AND (b.hi IS NULL OR t.金額 <  b.hi)
GROUP BY t.金額, t.期待する区分
HAVING COUNT(b.no) <> 1 OR MIN(b.no) <> t.期待する区分;   -- 1行も返らなければ合格

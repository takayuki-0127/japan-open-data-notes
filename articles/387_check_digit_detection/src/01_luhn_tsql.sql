-- 387 ルーン（モジュラス10）の検査（T-SQL。SQL Server 本体では動かしていません＝未検証）
-- member(no)：12桁の文字列。右端が検査用の桁
WITH p AS (                                   -- 1〜12 の連番
  SELECT v AS pos FROM (VALUES (1),(2),(3),(4),(5),(6),(7),(8),(9),(10),(11),(12)) AS t(v)
),
d AS (
  SELECT m.no, p.pos,
         CAST(SUBSTRING(m.no, LEN(m.no) - p.pos + 1, 1) AS INT) AS v          -- 右から pos 番目の数字
  FROM member AS m
  CROSS JOIN p
),
s AS (
  SELECT no,
         SUM(CASE WHEN pos % 2 = 0
                  THEN CASE WHEN v * 2 > 9 THEN v * 2 - 9 ELSE v * 2 END
                  ELSE v END) AS total
  FROM d
  GROUP BY no
)
SELECT m.no,
       CASE WHEN s.total % 10 = 0 THEN 1 ELSE 0 END AS ok                      -- 0 の行が、検査で止まる番号
FROM member AS m
JOIN s ON s.no = m.no;
-- 注意：番号に数字以外が混じる行は、先に TRY_CONVERT や LIKE '%[^0-9]%' で分けておく

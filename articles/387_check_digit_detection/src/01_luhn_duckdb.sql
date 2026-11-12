-- 387 ルーン（モジュラス10）の検査を SQL で書く（DuckDB で実行）
-- member(no)：12桁の文字列。右端が検査用の桁。右から数えて偶数番目の桁を2倍し、2桁になったら各桁を足す
WITH d AS (
  SELECT m.no, p.pos,
         CAST(SUBSTR(m.no, LENGTH(m.no) - p.pos + 1, 1) AS INTEGER) AS v      -- 右から pos 番目の数字
  FROM member AS m
  CROSS JOIN (SELECT UNNEST(RANGE(1, 13)) AS pos) AS p
),
s AS (
  SELECT no,
         SUM(CASE WHEN pos % 2 = 0
                  THEN CASE WHEN v * 2 > 9 THEN v * 2 - 9 ELSE v * 2 END
                  ELSE v END) AS total
  FROM d
  GROUP BY no
)
SELECT m.no, (s.total % 10 = 0) AS ok
FROM member AS m
JOIN s ON s.no = m.no
ORDER BY m.rowid;

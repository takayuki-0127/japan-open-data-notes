-- 463 連番の抜けと重複の確かめ方（T-SQL 版）
-- ※ SQL Server 本体では動かしていません（未検証）。同じ中身を DuckDB で実行して確かめています（a463_sequence.py）。
-- 表：dbo.slips(slip_no VARCHAR(20), prefix CHAR(1), yr INT, serial INT)   … slip_no は 'A-2025-000123' の形
--     dbo.void_numbers(prefix, yr, serial)     … 取消で欠番にした番号
--     dbo.issued(prefix, yr, last_no)          … 発番の控え（組ごとの最後の番号）

-- ② 組（接頭辞×年）ごとに、最大−最小＋1 と件数を比べる
SELECT prefix, yr, MAX(serial) - MIN(serial) + 1 AS expected, COUNT(*) AS n,
       MAX(serial) - MIN(serial) + 1 - COUNT(*) AS diff
FROM dbo.slips GROUP BY prefix, yr;

-- ③ 前の番号との差（1でなければ、抜けか重複）
WITH x AS (
  SELECT prefix, yr, serial,
         serial - LAG(serial) OVER (PARTITION BY prefix, yr ORDER BY serial) AS d
  FROM dbo.slips)
SELECT prefix, yr, serial - d + 1 AS missing_from, serial - 1 AS missing_to, d
FROM x WHERE d <> 1;          -- d = 0 は重複、d > 1 は抜け

-- 重複
SELECT prefix, yr, serial, COUNT(*) AS n FROM dbo.slips GROUP BY prefix, yr, serial HAVING COUNT(*) > 1;

-- ⑥ 発番の控えの最後の番号まで番号の一覧を作り、伝票にも取消の欠番にもない番号を出す
--    （GENERATE_SERIES は SQL Server 2022 以降。それより前は数の表を使う）
SELECT i.prefix, i.yr, g.value AS serial
FROM dbo.issued AS i
CROSS APPLY GENERATE_SERIES(1, i.last_no) AS g
LEFT JOIN (SELECT DISTINCT prefix, yr, serial FROM dbo.slips) AS s
       ON s.prefix = i.prefix AND s.yr = i.yr AND s.serial = g.value
LEFT JOIN dbo.void_numbers AS v
       ON v.prefix = i.prefix AND v.yr = i.yr AND v.serial = g.value
WHERE s.serial IS NULL AND v.serial IS NULL;

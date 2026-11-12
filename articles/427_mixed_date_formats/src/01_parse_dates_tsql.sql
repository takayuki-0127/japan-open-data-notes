-- 427 書き方が混ざった日付の列を読む（T-SQL 版。SQL Server 本体では未検証）
-- raw_dates(row_id int, source varchar(10), s nvarchar(30))

-- ① 書式を1つに決めて読む（年/月/日）。合わない行は NULL になる
SELECT row_id, TRY_CONVERT(date, s, 111) AS d FROM raw_dates;

-- ② 書き方ごとに判定して読む（西暦の主な形だけ）
SELECT row_id,
  CASE
    WHEN s LIKE '[12][0-9][0-9][0-9]/%/%'      THEN TRY_CONVERT(date, s, 111)          -- 2025/1/5
    WHEN s LIKE '[12][0-9][0-9][0-9]-[01][0-9]-[0-3][0-9]' THEN TRY_CONVERT(date, s, 23) -- 2025-01-05
    WHEN s LIKE '[12][0-9][0-9][0-9][01][0-9][0-3][0-9]'   THEN TRY_CONVERT(date, s, 112) -- 20250105
    WHEN s LIKE '%/%/[12][0-9][0-9][0-9]' AND source = 'US' THEN TRY_CONVERT(date, s, 101) -- 月/日/年
    WHEN s LIKE '%/%/[12][0-9][0-9][0-9]' AND source = 'EU' THEN TRY_CONVERT(date, s, 103) -- 日/月/年
    WHEN s LIKE '[0-9][0-9]/%/%' AND source = 'OLD' THEN TRY_CONVERT(date, s, 11)       -- 25/1/5（年2桁）
    WHEN s NOT LIKE '%[^0-9]%' AND LEN(s) = 5   THEN DATEADD(day, CAST(s AS int), '1899-12-30') -- 表計算の通し番号
  END AS d
FROM raw_dates;
-- 和暦（R7.1.5、令和7年1月5日、令和元年…）は、元号の表を別に持ち、
-- 「元号の始まりの年 + 和暦の年 - 1」で西暦に直してから DATEFROMPARTS で組み立てる。

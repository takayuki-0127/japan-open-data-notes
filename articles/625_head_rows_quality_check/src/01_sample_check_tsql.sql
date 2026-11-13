-- T-SQL：未検証（SQL Server では動かしていない）
-- C1：先頭の n 行
SELECT SUM(bad) FROM (SELECT TOP (5000) bad FROM dbo.lines ORDER BY row_no) AS t;
-- C2：無作為に n 行（NEWID で並べる。大きな表では重い）
SELECT SUM(bad) FROM (SELECT TOP (5000) bad FROM dbo.lines ORDER BY NEWID()) AS t;
-- C3：100の区間に分けて、区間ごとに50行ずつ無作為に
SELECT SUM(bad) FROM (
  SELECT bad, ROW_NUMBER() OVER (PARTITION BY (row_no - 1) / 10000 ORDER BY NEWID()) AS k
  FROM dbo.lines
) AS t WHERE k <= 50;

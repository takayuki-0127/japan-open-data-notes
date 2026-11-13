-- 中身を確かめる行の取り方（DuckDB 版）。lines(row_no, bad)：bad=1 が異常な行
-- C1：先頭の n 行
SELECT SUM(bad) FROM (SELECT bad FROM lines ORDER BY row_no LIMIT 5000);
-- C2：無作為に n 行（DuckDB の SAMPLE、種を固定）
SELECT SUM(bad) FROM (SELECT bad FROM lines USING SAMPLE reservoir(5000 ROWS) REPEATABLE (625));
-- C3：100の区間に分けて、区間ごとに50行ずつ無作為に
SELECT SUM(bad) FROM (
  SELECT bad, ROW_NUMBER() OVER (PARTITION BY (row_no - 1) // 10000 ORDER BY hash(row_no, 625)) AS k
  FROM lines
) WHERE k <= 50;

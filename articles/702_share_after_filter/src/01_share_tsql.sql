-- T-SQL：未検証（SQL Server では動かしていない）
-- A 絞ってから割る
SELECT item, SUM(amount) AS amt,
       CAST(SUM(amount) AS float) / SUM(SUM(amount)) OVER () AS share_in_filter
FROM dbo.sales
WHERE category = N'食品'
GROUP BY item;
-- B 全体で割ってから絞る
WITH t AS (
  SELECT item, category, SUM(amount) AS amt,
         CAST(SUM(amount) AS float) / SUM(SUM(amount)) OVER () AS share_total
  FROM dbo.sales
  GROUP BY item, category)
SELECT item, amt, share_total FROM t WHERE category = N'食品';
-- C 上位10品目
WITH t AS (SELECT TOP (10) item, SUM(amount) AS amt FROM dbo.sales GROUP BY item ORDER BY amt DESC)
SELECT item, amt, CAST(amt AS float) / SUM(amt) OVER () AS share_in_top10 FROM t;

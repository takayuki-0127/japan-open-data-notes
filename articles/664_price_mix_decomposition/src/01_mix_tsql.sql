-- T-SQL：未検証（SQL Server では動かしていない）
WITH s AS (
  SELECT item, [year], qty, price, qty * 1.0 / SUM(qty) OVER (PARTITION BY [year]) AS share FROM dbo.items),
w AS (
  SELECT a.item, a.share AS s0, b.share AS s1, a.price AS p0, b.price AS p1
  FROM s AS a JOIN s AS b ON b.item = a.item AND a.[year] = 2024 AND b.[year] = 2025)
SELECT SUM(s0 * p0) AS avg0, SUM(s1 * p1) AS avg1,
       SUM(s0 * (p1 - p0)) AS price_first_price, SUM((s1 - s0) * p1) AS price_first_mix,
       SUM(s1 * (p1 - p0)) AS mix_first_price,  SUM((s1 - s0) * p0) AS mix_first_mix,
       SUM((s1 - s0) * (p1 - p0)) AS interaction
FROM w;

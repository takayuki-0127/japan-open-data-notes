-- 平均単価の前年比を、単価の効果と構成（ミックス）の効果に分ける（DuckDB 版）
-- items(item, category, year, qty, price)  year は 2024 と 2025
WITH s AS (
  SELECT item, year, qty, price, qty * 1.0 / SUM(qty) OVER (PARTITION BY year) AS share FROM items),
w AS (
  SELECT a.item, a.share AS s0, b.share AS s1, a.price AS p0, b.price AS p1
  FROM s AS a JOIN s AS b ON b.item = a.item AND a.year = 2024 AND b.year = 2025)
SELECT SUM(s0 * p0) AS avg0, SUM(s1 * p1) AS avg1,
       SUM(s0 * (p1 - p0)) AS price_first_price, SUM((s1 - s0) * p1) AS price_first_mix,
       SUM(s1 * (p1 - p0)) AS mix_first_price,  SUM((s1 - s0) * p0) AS mix_first_mix,
       SUM((s1 - s0) * (p1 - p0)) AS interaction
FROM w;
-- 同じことを、品目ではなく分類（category）の単位で行う
WITH c AS (
  SELECT category, year, SUM(qty) AS qty, SUM(qty * price) / SUM(qty) AS price FROM items GROUP BY category, year),
s AS (SELECT category, year, price, qty * 1.0 / SUM(qty) OVER (PARTITION BY year) AS share FROM c),
w AS (SELECT a.category, a.share AS s0, b.share AS s1, a.price AS p0, b.price AS p1
      FROM s AS a JOIN s AS b ON b.category = a.category AND a.year = 2024 AND b.year = 2025)
SELECT SUM(s0 * (p1 - p0)) AS price_first_price, SUM((s1 - s0) * p1) AS price_first_mix,
       SUM(s1 * (p1 - p0)) AS mix_first_price,  SUM((s1 - s0) * p0) AS mix_first_mix
FROM w;

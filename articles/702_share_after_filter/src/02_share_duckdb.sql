-- 構成比を、絞ってから割るか、全体で割ってから絞るか（DuckDB 版）
-- sales(line_id, item, category, amount)
-- A 絞ってから割る（分母は絞った中の合計）
SELECT item, SUM(amount) AS amt,
       SUM(amount) / SUM(SUM(amount)) OVER () AS share_in_filter
FROM sales
WHERE category = '食品'
GROUP BY item
ORDER BY item;
-- B 全体で割ってから絞る（分母は全体の合計）
WITH t AS (
  SELECT item, category, SUM(amount) AS amt,
         SUM(amount) / SUM(SUM(amount)) OVER () AS share_total
  FROM sales
  GROUP BY item, category)
SELECT item, amt, share_total
FROM t
WHERE category = '食品'
ORDER BY item;
-- C 上位10品目に絞ってから割る
WITH t AS (SELECT item, SUM(amount) AS amt FROM sales GROUP BY item ORDER BY amt DESC LIMIT 10)
SELECT item, amt, amt / SUM(amt) OVER () AS share_in_top10
FROM t
ORDER BY item;

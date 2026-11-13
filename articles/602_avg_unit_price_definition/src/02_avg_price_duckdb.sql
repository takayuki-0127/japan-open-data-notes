-- 品目ごとの平均単価を3通りで出す（DuckDB 版）。sales_lines(line_id, item_id, sold_on, qty, unit_price, amount)
SELECT item_id,
       AVG(unit_price)                    AS p_simple,     -- U1 明細の単価の平均（1行を同じ重さで数える）
       SUM(amount) * 1.0 / SUM(qty)       AS p_weighted,   -- U0 金額の合計÷数量の合計（1個あたりの平均）
       SUM(qty)                           AS qty,
       SUM(amount)                        AS amount
FROM sales_lines
GROUP BY item_id;
-- U2 日ごとの平均単価をさらに平均する（平均の平均）
SELECT item_id, AVG(p_day) AS p_daily_mean
FROM (SELECT item_id, sold_on, AVG(unit_price) AS p_day FROM sales_lines GROUP BY item_id, sold_on) AS t
GROUP BY item_id;

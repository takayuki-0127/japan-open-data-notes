-- T-SQL：未検証（SQL Server では動かしていない）
-- 注意：unit_price・amount・qty が整数型だと AVG と割り算が整数になるので、1.0 を掛けて小数にする
SELECT item_id,
       AVG(unit_price * 1.0)                         AS p_simple,
       SUM(amount) * 1.0 / NULLIF(SUM(qty), 0)       AS p_weighted,
       SUM(qty) AS qty, SUM(amount) AS amount
FROM dbo.sales_lines
GROUP BY item_id;

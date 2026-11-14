-- 明細を月ごとに集計する（DuckDB）。Excel で開く前に、SQL で件数と合計を出しておく
SELECT strftime(sale_date, '%Y-%m') AS month,
       COUNT(*)    AS n_rows,
       SUM(amount) AS amount
FROM details
GROUP BY month
ORDER BY month;

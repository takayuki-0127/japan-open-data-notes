-- 入力表とは別に、SQL で月ごとの件数と合計を出して見比べる（DuckDB）
SELECT strftime(entry_date, '%Y-%m') AS month,
       COUNT(*)    AS n_rows,
       SUM(amount) AS amount
FROM entries
GROUP BY month
ORDER BY month;

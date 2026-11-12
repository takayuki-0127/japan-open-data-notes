-- ② だけを単独で実行する版（DuckDB）
-- ①③と同じ SELECT に書くと、DuckDB は「日付＋順番」の並びを②にも使い回すので、②がたまたま正しく見える
SELECT acct, d, seq, amount,
       SUM(amount) OVER (PARTITION BY acct ORDER BY d
                         ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS bal_rows_date_only
FROM tx;

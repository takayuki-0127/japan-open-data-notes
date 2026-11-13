-- DuckDB で実行（1スレッド）
-- datediff('month') は境目の回数、date_sub('month') は満了した月数
SELECT contract_id,
       datediff('month', start_date, end_date)          AS months_boundary,
       date_sub('month', start_date, end_date)          AS months_full,
       datediff('day', start_date, end_date) // 30      AS months_days30
FROM contracts
ORDER BY contract_id;

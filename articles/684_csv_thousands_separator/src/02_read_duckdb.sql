-- 引用符ありの CSV：金額は文字として読み、「,」を除いてから数にする（DuckDB）。{path} はファイルの場所
SELECT SUM(CAST(REPLACE(amount, ',', '') AS BIGINT)) AS amount_sum
FROM read_csv('{path}', header = true, quote = '"',
              columns = {'date': 'VARCHAR', 'store': 'VARCHAR', 'item': 'VARCHAR', 'amount': 'VARCHAR', 'qty': 'BIGINT'});
-- 数字のままの CSV
SELECT SUM(amount) AS amount_sum
FROM read_csv('{path}', header = true,
              columns = {'date': 'VARCHAR', 'store': 'VARCHAR', 'item': 'VARCHAR', 'amount': 'BIGINT', 'qty': 'BIGINT'});

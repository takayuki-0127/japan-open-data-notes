-- DuckDB で実行（1スレッド）。12本の CSV を、見出しを読み分けて列の名前でそろえて読む
-- read_csv の最初の引数（ファイルの一覧）は Python から ['../data/monthly_01.csv', ...] の形で差し込む
SELECT strftime(CAST(sales_date AS DATE), '%Y-%m') AS ym,
       COUNT(*)                                       AS rows,
       SUM(CAST(amount AS BIGINT))                    AS amount
FROM read_csv(:files, header = true, union_by_name = true, all_varchar = true)
GROUP BY 1
ORDER BY 1;

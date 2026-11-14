-- 同じ CSV を DuckDB で読む（DuckDB 版）。DuckDB の read_csv は、既定では空欄だけを NULL にする
SELECT region, COUNT(*) AS n, SUM(amount) AS amount
FROM read_csv('{CSV}')
GROUP BY region ORDER BY region NULLS LAST;
-- 地域が NULL の行を数える
SELECT COUNT(*) FILTER (WHERE region IS NULL) AS n_null_region
FROM read_csv('{CSV}');
-- 文字の列を、欠けを表す文字の候補で確かめる
SELECT region, COUNT(*) AS n
FROM read_csv('{CSV}')
WHERE upper(region) IN ('NA', 'N/A', 'NULL', 'NONE', 'NAN', '#N/A')
GROUP BY region;

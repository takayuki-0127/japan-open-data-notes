-- 30 データのテスト：どれも「問題のある行の数」を返す。0 なら合格（サンプルマート（架空）、合成データ）
-- SQL Server 互換の書き方。この記事では DuckDB で実行した。1つのテストは「-- test:」の行から次の「-- test:」の前まで。

-- test: T01 キーの重複（店×日が1行になっているか）
SELECT COUNT(*) AS n FROM (
    SELECT biz_date, store_id FROM mart_fact_store_day GROUP BY biz_date, store_id HAVING COUNT(*) > 1
) AS x;

-- test: T02 対応表にない店コード（受け取った対応表＋補正表で店番にできない POS の行）
SELECT COUNT(*) AS n FROM q_pos_unmapped;

-- test: T03 部門の参照（mart の部門が部門マスタにあるか）
SELECT COUNT(*) AS n FROM mart_fact_store_day_dept AS f
LEFT JOIN dim_category AS c ON c.category_id = f.category_id
WHERE c.category_id IS NULL;

-- test: T04 店の参照（mart の店が店マスタにあるか）
SELECT COUNT(*) AS n FROM mart_fact_store_day AS f
LEFT JOIN dim_store AS s ON s.store_id = f.store_id
WHERE s.store_id IS NULL;

-- test: T05 欠けた日（営業していたはずの店×日が mart にあるか。締めの日までの分）
SELECT COUNT(*) AS n FROM dim_store AS s
JOIN dim_date AS d ON d."date" >= s.open_date AND (s.close_date IS NULL OR d."date" <= s.close_date)
LEFT JOIN mart_fact_store_day AS f ON f.store_id = s.store_id AND f.biz_date = d."date"
WHERE f.store_id IS NULL AND d."date" <= (SELECT last_day FROM run_param);

-- test: T06 空の値（売上・人時・人件費・粗利が空の店×日）
SELECT COUNT(*) AS n FROM mart_fact_store_day
WHERE sales IS NULL OR labor_hours IS NULL OR labor_cost IS NULL OR gross_profit_before_waste IS NULL;

-- test: T07 部門の合計と店の合計（売上の差が10円を超える店×日。端数の丸めは許す）
SELECT COUNT(*) AS n FROM mart_fact_store_day
WHERE dept_sales IS NULL OR ABS(dept_sales - sales) > 10;

-- test: T08 会計との照合（店×月の売上が会計の売上高と0.1%以上ずれる、または片方にしかない）
SELECT COUNT(*) AS n FROM (
    SELECT m.store_id, m.ym, m.sales, a."売上高" AS acct_sales
    FROM mart_store_month AS m
    LEFT JOIN raw_acct_store_month AS a ON a."店番" = m.store_id AND a."年月" = m.ym
    WHERE m.ym <= (SELECT last_ym FROM run_param)
    UNION ALL
    SELECT a."店番", a."年月", NULL, a."売上高"
    FROM raw_acct_store_month AS a
    LEFT JOIN mart_store_month AS m ON m.store_id = a."店番" AND m.ym = a."年月"
    WHERE m.store_id IS NULL AND a."年月" <= (SELECT last_ym FROM run_param)
) AS x
WHERE x.sales IS NULL OR x.acct_sales IS NULL OR ABS(x.sales - x.acct_sales) > 0.001 * x.acct_sales;

-- test: T09 値の範囲（店×月の廃棄率が 0.5%〜6% の外、または人時が0以下の店×日）
SELECT COUNT(*) AS n FROM (
    SELECT store_id, ym FROM mart_store_month WHERE waste < 0.005 * sales OR waste > 0.06 * sales
    UNION ALL
    SELECT store_id, NULL FROM mart_fact_store_day WHERE labor_hours <= 0
) AS x;

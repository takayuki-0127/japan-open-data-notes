-- 402 集計済みの表（daily_sales）の更新の仕方と、元の表（sales_raw）との照合。T-SQL。SQL Server では未検証。
-- sales_raw(sale_id, sale_date, amount, created_at, updated_at)、sales_deleted_log(sale_id, sale_date, deleted_at)

-- A 当日分だけ足す
INSERT INTO daily_sales (sale_date, n, amount)
SELECT sale_date, COUNT(*), SUM(amount) FROM sales_raw WHERE sale_date = @today GROUP BY sale_date;

-- B 直近7日を作り直す（B' は 7 を 35 に）
DELETE FROM daily_sales WHERE sale_date >= DATEADD(day, -6, @today);
INSERT INTO daily_sales (sale_date, n, amount)
SELECT sale_date, COUNT(*), SUM(amount) FROM sales_raw
WHERE sale_date >= DATEADD(day, -6, @today) GROUP BY sale_date;

-- C 更新日時で、きょう変わった日だけ作り直す（消えた行は元の表に残らないので拾えない）
-- C' は、削除の記録（sales_deleted_log）の日も足す
SELECT DISTINCT sale_date INTO #touched FROM sales_raw
WHERE created_at >= @today OR updated_at >= @today;
-- C' のとき： INSERT INTO #touched SELECT DISTINCT sale_date FROM sales_deleted_log WHERE deleted_at >= @today;
DELETE FROM daily_sales WHERE sale_date IN (SELECT sale_date FROM #touched);
INSERT INTO daily_sales (sale_date, n, amount)
SELECT sale_date, COUNT(*), SUM(amount) FROM sales_raw
WHERE sale_date IN (SELECT sale_date FROM #touched) GROUP BY sale_date;

-- D 毎晩ぜんぶ作り直す
TRUNCATE TABLE daily_sales;
INSERT INTO daily_sales (sale_date, n, amount)
SELECT sale_date, COUNT(*), SUM(amount) FROM sales_raw GROUP BY sale_date;

-- 照合 K5：全期間を日ごとに比べる（合わない日を返す）
SELECT COALESCE(r.sale_date, s.sale_date) AS sale_date, r.amount AS raw_amount, s.amount AS summary_amount
FROM (SELECT sale_date, SUM(amount) AS amount FROM sales_raw GROUP BY sale_date) AS r
FULL JOIN daily_sales AS s ON s.sale_date = r.sale_date
WHERE COALESCE(r.amount, 0) <> COALESCE(s.amount, 0);

-- 照合 K4：全期間の合計を比べる（0.1%まで許す）
SELECT CASE WHEN ABS(s.a - r.a) > 0.001 * r.a THEN 'NG' ELSE 'OK' END
FROM (SELECT SUM(amount) AS a FROM sales_raw) AS r CROSS JOIN (SELECT SUM(amount) AS a FROM daily_sales) AS s;

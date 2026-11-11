-- F253 毎月の品質チェック（Q01〜Q05・Q08、Q06 は参照 a だけ）を SQL で書いたもの。
-- 入力のテーブル：cur（その月の店×日、そのまま）、cat（その月の店×日×部門）、hist（前の月までの確定の店×日）、
--                 expected（営業しているはずの店×日）、param（m0：月初の日、t_pos、t_waste：Q06 の線）
-- DuckDB で実行した。SQL Server で使うときは、MEDIAN を PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY x) OVER (PARTITION BY …) に、
-- LN を LOG に、DATE の足し引きを DATEADD に書き換える（この記事では SQL Server では動かしていない）。
-- 会社・数字はすべて架空（合成データ）。

CREATE OR REPLACE TABLE dq_flags AS
-- Q01 キーの重複
SELECT 'Q01' AS chk, store_id, biz_date, '行' AS metric FROM cur GROUP BY store_id, biz_date HAVING COUNT(*) > 1
UNION ALL
-- Q02 行の欠け（営業しているはずの日に行がない）と、営業日の外の行
SELECT 'Q02', e.store_id, e.biz_date, '行' FROM expected e LEFT JOIN (SELECT DISTINCT store_id, biz_date FROM cur) c
  ON c.store_id = e.store_id AND c.biz_date = e.biz_date WHERE c.store_id IS NULL
UNION ALL
SELECT DISTINCT 'Q02', c.store_id, c.biz_date, '営業日の外の行' FROM cur c LEFT JOIN expected e
  ON c.store_id = e.store_id AND c.biz_date = e.biz_date WHERE e.store_id IS NULL
UNION ALL
-- Q03 空の値
SELECT 'Q03', store_id, biz_date, m FROM (
  SELECT store_id, biz_date, CASE WHEN receipts IS NULL THEN '客数' END AS m FROM cur UNION ALL
  SELECT store_id, biz_date, CASE WHEN member_receipts IS NULL THEN '会員の客数' END FROM cur UNION ALL
  SELECT store_id, biz_date, CASE WHEN items IS NULL THEN '点数' END FROM cur UNION ALL
  SELECT store_id, biz_date, CASE WHEN sales IS NULL THEN '売上' END FROM cur UNION ALL
  SELECT store_id, biz_date, CASE WHEN gross_profit_before_waste IS NULL THEN '廃棄前の粗利' END FROM cur UNION ALL
  SELECT store_id, biz_date, CASE WHEN waste IS NULL THEN '廃棄' END FROM cur UNION ALL
  SELECT store_id, biz_date, CASE WHEN labor_hours IS NULL THEN '人時' END FROM cur UNION ALL
  SELECT store_id, biz_date, CASE WHEN labor_cost IS NULL THEN '人件費' END FROM cur) x WHERE m IS NOT NULL
UNION ALL
-- Q04 営業日のゼロ
SELECT 'Q04', store_id, biz_date, m FROM (
  SELECT store_id, biz_date, CASE WHEN sales <= 0 THEN '売上' END AS m FROM cur UNION ALL
  SELECT store_id, biz_date, CASE WHEN receipts <= 0 THEN '客数' END FROM cur UNION ALL
  SELECT store_id, biz_date, CASE WHEN items <= 0 THEN '点数' END FROM cur UNION ALL
  SELECT store_id, biz_date, CASE WHEN labor_hours <= 0 THEN '人時' END FROM cur) x WHERE m IS NOT NULL
UNION ALL
-- Q05 ほかの日と同じ値（その月と、前の7日）
SELECT 'Q05', a.store_id, a.biz_date, '客数・点数・売上' FROM (SELECT DISTINCT store_id, biz_date, receipts, items, ROUND(sales, 0) AS s FROM cur WHERE sales > 0) a
  WHERE EXISTS (SELECT 1 FROM (SELECT store_id, biz_date, receipts, items, ROUND(sales, 0) AS s FROM cur WHERE sales > 0
                               UNION ALL SELECT h.store_id, h.biz_date, h.receipts, h.items, ROUND(h.sales, 0) FROM hist h, param p
                               WHERE h.biz_date >= p.m0 - INTERVAL 7 DAY AND h.biz_date < p.m0) b
                WHERE b.store_id = a.store_id AND b.receipts = a.receipts AND b.items = a.items AND b.s = a.s AND b.biz_date <> a.biz_date)
UNION ALL
-- Q08 部門の合計と店の売上
SELECT 'Q08', COALESCE(c.store_id, d.store_id), COALESCE(c.biz_date, d.biz_date),
       CASE WHEN d.store_id IS NULL THEN '部門の行なし' WHEN c.store_id IS NULL THEN '店の行なし' ELSE '部門の合計÷店の売上' END
FROM (SELECT DISTINCT ON (store_id, biz_date) store_id, biz_date, sales FROM cur) c
FULL OUTER JOIN (SELECT store_id, biz_date, SUM(sales) AS dept_sales FROM cat GROUP BY store_id, biz_date) d
  ON c.store_id = d.store_id AND c.biz_date = d.biz_date
WHERE d.store_id IS NULL OR c.store_id IS NULL OR (c.sales > 0 AND ABS(d.dept_sales - c.sales) > 0.005 * c.sales);

-- Q06（参照 a だけ）：月初の前の8週の、同じ曜日の中央値と比べる
CREATE OR REPLACE TABLE ref_a AS
SELECT h.store_id, DAYOFWEEK(h.biz_date) AS dw, MEDIAN(sales) AS sales, MEDIAN(receipts) AS receipts, MEDIAN(items) AS items,
       MEDIAN(labor_hours) AS labor_hours, MEDIAN(waste) AS waste
FROM hist h, param p WHERE h.biz_date >= p.m0 - INTERVAL 56 DAY AND h.biz_date < p.m0 GROUP BY h.store_id, DAYOFWEEK(h.biz_date);

INSERT INTO dq_flags
SELECT 'Q06', c.store_id, c.biz_date, m FROM (
  SELECT c.store_id, c.biz_date, '売上' AS m, c.sales AS v, r.sales AS r, p.t_pos AS t FROM cur c JOIN ref_a r ON r.store_id = c.store_id AND r.dw = DAYOFWEEK(c.biz_date), param p UNION ALL
  SELECT c.store_id, c.biz_date, '客数', c.receipts, r.receipts, p.t_pos FROM cur c JOIN ref_a r ON r.store_id = c.store_id AND r.dw = DAYOFWEEK(c.biz_date), param p UNION ALL
  SELECT c.store_id, c.biz_date, '点数', c.items, r.items, p.t_pos FROM cur c JOIN ref_a r ON r.store_id = c.store_id AND r.dw = DAYOFWEEK(c.biz_date), param p UNION ALL
  SELECT c.store_id, c.biz_date, '人時', c.labor_hours, r.labor_hours, p.t_pos FROM cur c JOIN ref_a r ON r.store_id = c.store_id AND r.dw = DAYOFWEEK(c.biz_date), param p UNION ALL
  SELECT c.store_id, c.biz_date, '廃棄', c.waste, r.waste, p.t_waste FROM cur c JOIN ref_a r ON r.store_id = c.store_id AND r.dw = DAYOFWEEK(c.biz_date), param p
) c WHERE v > 0 AND r > 0 AND ABS(LN(v / r)) > LN(t);

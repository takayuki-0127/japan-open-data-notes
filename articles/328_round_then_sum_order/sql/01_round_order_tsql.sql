-- 328 税の端数を丸める場所（T-SQL 版）。SQL Server 本体では動かしていません（未検証）。DuckDB 版は src/a328_round_order.py。
-- lines(invoice_id, customer_id, tax_rate, net)：net は税抜の金額（整数の円）、tax_rate は 8 か 10。切り捨ての例
-- 税額は net * tax_rate / 100 を整数の割り算で出す（小数の型を通さない）

-- ① 明細ごとに丸める
SELECT invoice_id, SUM(net * tax_rate / 100) AS tax FROM lines GROUP BY invoice_id;

-- ② 伝票の中で、税率ごとに1回
SELECT invoice_id, SUM(tax) AS tax
FROM (SELECT invoice_id, tax_rate, SUM(net * tax_rate) / 100 AS tax FROM lines GROUP BY invoice_id, tax_rate) t
GROUP BY invoice_id;

-- ③ 伝票全体で1回
SELECT invoice_id, SUM(net * tax_rate) / 100 AS tax FROM lines GROUP BY invoice_id;

-- ④ 得意先の月合計で、税率ごとに1回
SELECT customer_id, SUM(tax) AS tax
FROM (SELECT customer_id, tax_rate, SUM(CAST(net AS BIGINT) * tax_rate) / 100 AS tax FROM lines GROUP BY customer_id, tax_rate) t
GROUP BY customer_id;

-- 472 返品をどの月に置くか（T-SQL の書き方。SQL Server 本体では動かしていない＝未検証。同じ文を DuckDB で実行して確かめた）
-- sales(order_id, sale_date DATE, amount)   returns(order_id, return_date DATE, amount)  返品は全額の返品
-- ① 売れた月に戻す：返品を、元の売上の月から引く
SELECT YEAR(s.sale_date) * 100 + MONTH(s.sale_date) AS ym,
       SUM(s.amount) - SUM(COALESCE(r.amount, 0)) AS net_by_sale_month
FROM sales s LEFT JOIN returns r ON r.order_id = s.order_id
GROUP BY YEAR(s.sale_date) * 100 + MONTH(s.sale_date);

-- ② 返ってきた月で引く：その月の売上から、その月に返ってきた分を引く
SELECT g.ym, g.gross - COALESCE(t.ret, 0) AS net_by_return_month
FROM (SELECT YEAR(sale_date) * 100 + MONTH(sale_date) AS ym, SUM(amount) AS gross
      FROM sales GROUP BY YEAR(sale_date) * 100 + MONTH(sale_date)) g
LEFT JOIN (SELECT YEAR(return_date) * 100 + MONTH(return_date) AS ym, SUM(amount) AS ret
           FROM returns GROUP BY YEAR(return_date) * 100 + MONTH(return_date)) t ON t.ym = g.ym;

-- ③ ある日（締めの日）までに分かっていた返品だけで、①を出す（あとから過去の月が動く様子を見る）
--   …LEFT JOIN returns r ON r.order_id = s.order_id AND r.return_date <= @as_of

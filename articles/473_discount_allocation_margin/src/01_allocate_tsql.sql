-- 473 注文全体への値引きを明細に割り振る（T-SQL の書き方。SQL Server 本体では動かしていない＝未検証。同じ文を DuckDB で実行して確かめた）
-- lines(order_id, line_no, product_id, qty, amount, cost)   orders(order_id, discount)   discount は注文全体への値引き（円）
SELECT l.order_id, l.line_no, l.product_id, l.amount, l.cost, o.discount,
       -- ① 金額の割合で割り振る（四捨五入。合計が合わない注文が出る）
       ROUND(o.discount * l.amount / SUM(l.amount) OVER (PARTITION BY l.order_id), 0) AS alloc_amount_round,
       -- ② 数量の割合で割り振る
       ROUND(o.discount * l.qty * 1.0 / SUM(l.qty) OVER (PARTITION BY l.order_id), 0) AS alloc_qty_round,
       -- ③ いちばん高い明細に寄せる（同額なら行番号の小さいほう）
       CASE WHEN ROW_NUMBER() OVER (PARTITION BY l.order_id ORDER BY l.amount DESC, l.line_no) = 1
            THEN o.discount ELSE 0 END AS alloc_top
FROM lines l JOIN orders o ON o.order_id = l.order_id;

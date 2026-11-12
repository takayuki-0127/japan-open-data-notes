-- 照合のクエリ（5つ）。{JOINED} には確かめたい結合（FROM 句）が入る。T-SQL の書き方、DuckDB で実行
-- name: C1_結合の前後で行数を比べる
SELECT (SELECT COUNT(*) FROM dbo.orders) AS before_rows,
       (SELECT COUNT(*) FROM {JOINED}) AS after_rows;

-- name: C2_結合後に注文番号が重なっていないか
SELECT COUNT(*) - COUNT(DISTINCT o.order_id) AS extra_rows
FROM {JOINED};

-- name: C3_結合後に注文番号が減っていないか
SELECT (SELECT COUNT(*) FROM dbo.orders) - COUNT(DISTINCT o.order_id) AS lost_orders
FROM {JOINED};

-- name: C4_合計を元の表の合計と比べる
SELECT (SELECT SUM({SRC_COL}) FROM {SRC_TABLE}) AS source_total,
       (SELECT SUM({COL}) FROM {JOINED}) AS joined_total;

-- name: C5_つなぐ相手のキーが重なっていないか
SELECT COUNT(*) AS dup_keys
FROM (SELECT {KEY} FROM {RIGHT} GROUP BY {KEY} HAVING COUNT(*) > 1) AS d;

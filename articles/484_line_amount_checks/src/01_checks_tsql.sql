-- 484 明細の金額の確かめ（T-SQL 版。SQL Server では動かしていない：未検証）
-- lines(line_id, item, unit_price decimal(12,1), qty int, discount money, amount money)
-- price_master(item, price)
SELECT l.line_id,
       CASE WHEN l.amount <> l.unit_price * l.qty THEN 1 ELSE 0 END                                   AS c1_exact,
       CASE WHEN ABS(l.amount - l.unit_price * l.qty) > 1 THEN 1 ELSE 0 END                           AS c2_tol1yen,
       CASE WHEN ABS(l.amount - l.unit_price * l.qty) > 0.005 * ABS(l.unit_price * l.qty) THEN 1 ELSE 0 END AS c3_tol05pct,
       CASE WHEN ABS(l.amount - (l.unit_price * l.qty - l.discount)) > 0.5 THEN 1 ELSE 0 END          AS c4_disc_half,
       CASE WHEN ABS(l.amount - (l.unit_price * l.qty - l.discount)) >= 1 THEN 1 ELSE 0 END           AS c5_disc_1yen,
       CASE WHEN SIGN(l.amount) <> SIGN(l.qty) AND l.amount <> 0 THEN 1 ELSE 0 END                     AS c6_sign,
       CASE WHEN l.unit_price <> m.price THEN 1 ELSE 0 END                                            AS c7_master
FROM lines AS l
JOIN price_master AS m ON m.item = l.item;
-- 「値引きを引いて差1円未満」「符号」「単価をマスタと照合」の3つを OR でつないだものが、ここでの一番よい組み合わせ
-- money 型と decimal 型の掛け算の桁の扱いは SQL Server で確かめていない
